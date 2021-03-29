#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Core configuration classes and methods.
'''
# pylint: disable=too-many-lines
import os
import inspect
from collections import OrderedDict
from functools import partial
from typing import Union, Any, Optional, Dict, Iterator, Tuple, List, Callable, Type
from argparse import ArgumentParser, Namespace
import warnings

from .encryption import KeyFile

ConfigValidator = Callable[['Config'], None]
FieldValidator = Callable[['Config', Any], Any]
SchemaField = Union['BaseField', 'ConfigType']
TFormatFactory = Callable[[], "ConfigFormat"]


def isconfigtype(obj: Any) -> bool:
    '''
    Check if an object is configuration type (is class and is subclass of :class:`ConfigType`).

    :param obj: object to check
    :returns: the object is a configuration type
    '''
    return inspect.isclass(obj) and issubclass(obj, ConfigType)


class ValidationError(ValueError):
    '''
    An error that occurs while validating a field's value or entire configuration.
    '''

    def __init__(self, config: 'Config', field: Optional['BaseField'], exc: Union[str, Exception],
                 ref_path: str = None):
        '''
        :param config: parent configuration
        :param field: field being validated, None if the entire config was being validated
        :param exc: original exception
        :param ref_path: override reference path to the field or configuration that failed
            validation
        '''
        super().__init__(config, field, exc, ref_path)
        self.config = config
        self.field = field
        self.exc = exc
        self._ref_path = ref_path

    def __str__(self):
        if isinstance(self.exc, OSError):
            msg = self.exc.strerror
        else:
            msg = str(self.exc)

        path = self.ref_path
        if isinstance(self.field, Field) and self.field._name:
            path += " (%s)" % self.field._name

        return '%s: %s' % (path, msg)

    @property
    def ref_path(self) -> str:
        '''
        :returns: the full path to the field or configuration that failed validation
        '''
        if self._ref_path:
            return self._ref_path

        path = self.config._ref_path
        if self.field:
            if path:
                path += "." + self.field._key
            else:
                path = self.field._key
        return path


class ContainerValueMixin:
    '''
    An abstract base class for container value (list, dict, etc.)
    '''

    def _get_item_position(self, item: Any) -> str:
        '''
        Return the position for a given item. This method is called when generate the full path to
        a configuration item.

        :param item: container item
        :returns: the position of the item
        '''
        raise NotImplementedError()


class VirtualFieldMixin:
    '''
    Field mixin to flag a field as virtual.
    '''


class InstanceMethodFieldMixin:
    '''
    Field mixin to bind an instance method to a configuration object.
    '''


class FeatureFlagFieldMixin:
    '''
    Field mixin to flag a the schema as enabled or disabled.
    '''
    def is_feature_enabled(self, cfg: 'Config') -> bool:
        '''
        Check if the feature is enabled.

        :returns: ``True`` if the feature is enabled and ``False`` if it is not.
        '''
        raise NotImplementedError()


class IncludeFieldMixin:
    '''
    Field mixin to include a configuration file.
    '''

    def include(self, config: 'Config', fmt: 'ConfigFormat', filename: str, base: dict) -> dict:
        '''
        Include a configuration file and combine it with an already parsed basic value tree. Values
        defined in the included file will overwrite values in the base tree. Nested trees (``dict``
        objects) will be combined using a :meth:`dict.update` like method, :meth:`combine_trees`.

        :param config: configuration object
        :param fmt: configuration file format that will parse the included file
        :param filename: included file path
        :param base: base config value tree
        :returns: the new basic value tree containing the base tree and the included tree
        '''
        raise NotImplementedError()


class BaseField:
    '''
    Base class for all fields in a schema.
    '''

    def __init__(self, key: str = None, name: str = None, schema: 'Schema' = None):
        '''
        :param key: field key
        :param name: descriptive name
        :param schema: owning schema
        '''
        self._key: str = key or ''
        self._name = name
        self._schema = schema

    def __setkey__(self, schema: 'Schema', key: str) -> None:
        '''
        Set the field key and bind it to a schema.

        :param schema: owning schema
        :param key: field key
        '''
        self._schema = schema
        self._key = key

    def __getval__(self, cfg: 'Config') -> Any:
        '''
        Retrieve the value from the config. The default implementation retrieves the value from the
        config by the field *key*.

        :param cfg: current config
        :returns: the value stored in the config
        '''
        return cfg._data[self._key]

    def __setdefault__(self, cfg: 'Config') -> None:
        '''
        Set the default value in the configuration. Subclasses should set the field's default value
        directly in the ``cfg._data`` dictionary. For example:

        .. code-block:: python

            def __setdefault__(self, cfg: 'Config') -> None:
                cfg._data[self._key] = "Hello, world!"
        '''

    @property
    def full_path(self) -> str:
        '''
        **(Deprecated, will be removed in v1.0.0)** get the full path to the field

        :returns: the full path to this configuration
        '''
        warnings.warn("BaseField.full_path is deprecated and will be removed in v1.0.0, use "
                      "cincoconfig.item_ref_path() instead", DeprecationWarning)
        return self._ref_path

    @property
    def _ref_path(self) -> str:
        '''
        Get the full reference path to the schema field. For example:

        .. code-block::

            >>> schema = Schema()
            >>> schema.x.y.z = Field()
            >>> schema.x.y.z._ref_path
            'x.y.z'
        '''
        path = [self._key]
        schema = self._schema
        while schema:
            if schema._key:
                path.append(schema._key)
            schema = schema._schema

        return '.'.join(reversed(path))


class Field(BaseField):
    '''
    The base configuration field. Fields provide validation and the mechanisms to retrieve and set
    values from a :class:`Config`. Field's are composable and reusable so they should not store
    state or store the field value.

    Validation errors should raise a :class:`ValueError` exception with a brief message.

    There are three steps to validating a value:

    1. :meth:`validate` - checks the value against the *required* parameter and then calls:
    2. :meth:`_validate` - validate function that is implemented in subclasses of ``Field``
    3. ``Field.validator`` - custom validator method specified when the field is created

    The pseudo code for the :meth:`validate` function:

    .. code-block:: python
        :linenos:

        def validate(self, cfg, value):
            if value is None and self.required:
                raise ValueError

            value = self._validate(cfg, value)
            if self.validator:
                value = self.validate(cfg, value)
            return value

    Since each function in the validation chain returns the value, each validator can transform
    the value. For example, the :class:`BoolField` ``_validate`` method converts the string value
    to a :class:`bool`.

    Each Field has the following lifecycle:

    1. ``__init__`` - created by the application
    2. :meth:`__setkey__` - the field is added to a :class:`Schema`
    3. :meth:`__setdefault__` - the field is added to a config and the config is populated with the
        default value

    Whenever a config value is set, the following methods are called in this order:

    1. :meth:`validate` / :meth:`_validate` / ``validator`` - validation chain
    2. :meth:`__setval__` - set a validated value to the config

    Finally, whenever code retrieves a config value, the :meth:`__getval__` is called.

    Most field subclasses only need to implement the ``_validate`` method and most do not need to
    implement the ``__setkey__``, ``__setdefault__``, ``__getval__`` and ``__setval__`` methods,
    unless the field needs to modify the default behavior of these methods.

    The Field ``_key`` is used to set and reference the value in the config.

    Each Field subclass can define a class or instance level ``storage_type`` which holds the
    annotation of the value being stored in memory.

    .. _field-env-variables:

    **Environment Variables**

    Fields can load their default value from an environment variable. The Schema and Field accept
    an ``env`` argument in the constructor that controls whether and how environment variables are
    loaded. The default behavior is to not load any environment variables and to honor the
    :attr:`Field.default` value.

    There are two ways to load a field's default value from an environment variable.

    - ``Schema.env``: Provide ``True`` or a string.
    - ``Field.env``: Provide ``True`` or a string.

    When ``Schema.env`` or ``Field.env`` is ``None`` (the default), the environment variable
    configuration is inherited from the parent schema. A value of ``True`` will load the the
    field's default value from an autogenerated environment variable name, based on the field's
    full path. For example:

    .. code-block:: python

        schema = Schema(env=True)
        schema.mode = ApplicationModeField(env="APP_MODE")
        schema.port = PortField(env=False)

        schema.db.host = HostnameField()

        schema.auth = Schema(env="SECRET")
        schema.auth.username = StringField()

    - The top-level schema is configured to autogenerate and load environment variables for all
      fields.
    - ``mode`` is loaded from the ``APP_MODE`` environment variable.
    - ``port`` is not loaded from any the environment variabale.
    - ``db.host`` is loaded from the ``DB_HOST`` environment variable.
    - The ``auth`` schema has a environment variable prefix of ``SECRET``. All children and nested
      fields/schemas will start with ``SECRET_``.
    - The ``auth.username`` field is loaded from the ``SECRET_USERNAME`` environment variable.
    '''
    storage_type = Any

    def __init__(self, *, key: str = None, schema: 'Schema' = None, name: str = None,
                 required: bool = False, default: Union[Callable, Any] = None,
                 validator: FieldValidator = None, sensitive: bool = False,
                 description: str = None, help: str = None, env: Union[bool, str] = None):
        '''
        All builtin Fields accept the following keyword parameters.

        :param name: field friendly name, used for error messages and documentation
        :param key: the key of the field in the config, this is typically not specified and,
            instead the :meth:`__setkey__` will be called by the config
        :param required: the field is required and a :class:`ValueError` will be raised if the
            value is ``None``
        :param default: the default value, which can be a called that is invoke with no arguments
            and should return the default value
        :param validator: an additional validator function that is invoked during validation
        :param sensitive: the field stores a sensitive value
        :param help: the field documentation
        '''
        super().__init__(name=name, key=key, schema=schema)
        self.required = required
        self._default = default
        self.validator = validator
        self.sensitive = sensitive
        self.description = description
        self.help = help.strip() if help else None
        self.env = env

    @property
    def short_help(self) -> Optional[str]:
        '''
        A short help description of the field. This is derived from the ``help`` attribute and is
        the first paragraph of text in ``help``. The intention is that ``short_help`` can be used
        for the field description and ``help`` will have the full documentation. For example:

        .. code-block:: python

            >>> field = Field(help="""
            ... This is a short description
            ... that can span multiple lines.
            ...
            ... This is more information.
            ... """)
            >>> print(field.short_help)
            this is a short description
            that can span multiple lines.

        :returns: the first paragraph of ``help``
        '''
        if self.help:
            return self.help.split('\n\n', 1)[0]
        return None

    @property
    def default(self) -> Any:
        '''
        :returns: the field's default value
        '''
        return self._default() if callable(self._default) else self._default

    @property
    def name(self):
        '''
        :returns: the field's friendly name: ``name or key``
        '''
        return self._name or self._key

    def _validate(self, cfg: 'Config', value: Any) -> Any:
        '''
        Subclass validation hook. The default implementation just returns ``value`` unchanged.
        '''
        return value

    def __setval__(self, cfg: 'Config', value: Any):
        '''
        Set the validated value in the config. The default implementation passes the value through
        the validation chain and then set's the validated value int the config.

        :param cfg: current config
        :param value: value to validated
        '''
        cfg._data[self._key] = value

    def validate(self, cfg: 'Config', value: Any) -> Any:
        '''
        Start the validation chain and verify that the value is specified if *required=True*.

        :param cfg: current config
        :param value: value to validate
        :returns: the validated value
        '''
        if self.required and value is None:
            raise ValueError('value is required')

        if value is None:
            return value

        value = self._validate(cfg, value)
        if self.validator:
            value = self.validator(cfg, value)

        return value

    def __setkey__(self, schema: 'Schema', key: str):
        '''
        Set the field's *_key*, which is called when the field is added to a schema. The default
        implementation just sets ``self._key = key``

        :param schema: the schema the field belongs to
        :param key: the field's unique key
        '''
        super().__setkey__(schema, key)

        if self.env is False:
            return

        if self.env is True or (self.env is None and isinstance(schema._env_prefix, str)):
            # Set our environment variable name based on the schema's prefix and our key
            if isinstance(schema._env_prefix, str) and schema._env_prefix:
                prefix = schema._env_prefix + '_'
            else:
                prefix = ''

            self.env = prefix + self._key.upper()

    def __setdefault__(self, cfg: 'Config') -> None:
        '''
        Set the default value of the field in the config. This is called when the config is first
        created.

        :param cfg: current config
        '''
        value = None

        if isinstance(self.env, str) and self.env:
            env_value = os.environ.get(self.env)
            if env_value:
                try:
                    env_value = self.validate(cfg, env_value)
                except ValidationError:
                    raise
                except Exception as exc:
                    raise ValidationError(cfg, self, exc) from exc
                else:
                    value = env_value

        if value is None:
            value = self.default

        cfg._data[self._key] = value

    def to_python(self, cfg: 'Config', value: Any) -> Any:
        '''
        Convert the basic value to a Python value. Basic values are serializable (ie. not complex
        types). The following must hold true for config file saving and loading to work:

        .. code-block:: python

            assert field.to_python(field.to_basic(value)) == value

        The default implementation just returns ``value``. This method is called when the config is
        loaded from a file and will only be called with the value associated with this field.

        In general, basic types are any types that can be represented in JSON: string, number,
        list, dict, boolean.

        :param cfg: current config
        :param value: value to convert to a Python type
        :returns: the converted Python type
        '''
        return value

    def to_basic(self, cfg: 'Config', value: Any) -> Any:
        '''
        Convert the Python value to the basic value.

        The default implementation just returns ``value``. This method is called when the config is
        saved to a file and will only be called with the value associated with this field.

        :param cfg: current config
        :param value: value to convert to a basic type
        :returns: the converted basic type
        '''
        return value


class AnyField(Field):
    '''
    A field that accepts any value and does not perform any validation beyond the base Field's
    *required* check.
    '''


class ConfigTypeField(BaseField):
    '''
    A field that wraps a :class:`ConfigType` object, created by the :meth:`~cincoconfig.make_type`
    method.
    '''

    def __init__(self, config_type: Type["ConfigType"], key: str = None, name: str = None):
        '''
        :param config_type: the ``ConfigType`` class
        '''
        super().__init__(key=key, name=name)
        self.config_type = config_type

    def __setdefault__(self, cfg: 'Config') -> None:
        cfg._data[self._key] = self.config_type(cfg)

    def __call__(self, cfg: 'Config' = None) -> 'ConfigType':
        '''
        Create an instance of the wrapped ``ConfigType``.

        :param cfg: parent configuration
        :returns: the config type instance
        '''
        return self.config_type(cfg)


class Schema(BaseField):
    '''
    A config schema containing all available configuration options. A schema's fields and hierarchy
    are built dynamically.

    .. code-block:: python

        schema = Schema()
        schema.mode = ApplicationModeField(default='production', required=True)
        schema.http.port = PortField(default=8080)
        # the previous line implicitly performs "schema.http = Schema(key='http')"
        schema.http.host = IPv4Address(default='127.0.0.1')

    Accessing a field that does not exist, such as ``schema.http`` in the above code, dynamically
    creates and adds a new ``Schema``.

    Once a schema is completely defined, a :class:`Config` is created by calling the schema. The
    config is populate with the default values specified for each field and can then load the
    configuration from a file.
    '''

    def __init__(self, key: str = None, name: str = None, dynamic: bool = False,
                 env: Union[str, bool] = None, schema: 'Schema' = None):
        # pylint: disable=too-many-arguments
        '''
        :param key: schema field key
        :param dynamic: configurations created from this schema are dynamic and can add fields not
            originally in the schema
            *_key*
        :param env: the environment variable prefix for this schema and all children schemas, for
            information, see :ref:`Field Environment Variables <field-env-variables>`
        '''
        super().__init__(key=key, schema=schema, name=name)
        self._dynamic = dynamic
        self._fields: Dict[str, BaseField] = OrderedDict()
        self._env_prefix = '' if env is True else env
        self._validators: List[ConfigValidator] = []

    @property
    def _feature_flag_fields(self) -> Iterator[FeatureFlagFieldMixin]:
        '''
        :returns: an iterator of all feature flag fields
        '''
        return (field for field in self._fields.values()
                if isinstance(field, FeatureFlagFieldMixin))

    def _is_feature_enabled(self, cfg: 'Config') -> bool:
        '''
        :returns: the feature is enabled (all :class:`FeatureFlagFieldMixin` fields returned
            ``True``)
        '''
        return all(field.is_feature_enabled(cfg) for field in self._feature_flag_fields)

    def __setkey__(self, schema: 'Schema', key: str) -> None:
        '''
        Field protocol, set the schema *_key* attribute.
        '''
        super().__setkey__(schema, key)

        if self._env_prefix is False:
            return

        if self._env_prefix is None and isinstance(schema._env_prefix, str):
            # Set our environment variable prefix to be "{parent}_{key}"
            prefix = (schema._env_prefix + '_') if schema._env_prefix else ''
            self._env_prefix = prefix + self._key.upper()

    def __setdefault__(self, cfg: 'Config') -> None:
        cfg._data[self._key] = Config(self, cfg)

    def _get_field(self, key: str) -> Optional[BaseField]:
        '''
        :returns: a field from the schema
        '''
        return self._fields.get(key)

    def __setattr__(self, name: str, value: Any) -> Any:
        '''
        :param name: attribute name
        :param value: field or schema to add to the schema
        '''
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            value = self._add_field(name, value)

        return value

    def _add_field(self, name: str, field: SchemaField) -> BaseField:
        '''
        Add a field to the schema. This method will call ``field.__setkey__(self, key)``.

        :returns: the added field (``field``)
        '''

        if isconfigtype(field):
            field = ConfigTypeField(field)  # type: ignore
        elif not isinstance(field, BaseField):
            raise TypeError("Schema fields must inherit from BaseField")

        self._fields[name] = field  # type: ignore
        field.__setkey__(self, name)
        return field  # type: ignore

    def __getattr__(self, name: str) -> BaseField:
        '''
        Retrieve a field by key or create a new ``Schema`` if the field doesn't exist.

        :param name: field or schema key
        '''
        return self._fields.get(name) or self._add_field(name, Schema())

    def __call__(self, parent: 'Config' = None, **data):
        '''
        Compile the schema into an initial config with default values set.
        '''
        return Config(self, **data)

    def __iter__(self) -> Iterator[Tuple[str, BaseField]]:
        '''
        Iterate over schema fields, produces as a list of tuples ``(key, field)``.
        '''
        yield from self._fields.items()

    def __getitem__(self, key: str) -> BaseField:
        '''
        :returns: field, equivalent to ``getattr(schema, key)``, however his method handles
            retrieving nested values. For example:

            .. code-block:: python

                >>> schema = Schema()
                >>> schema.x.y = IntField(default=10)
                >>> print(schema['x.y'])
                IntField(key='y', ...)
        '''
        key, _, subkey = key.partition('.')
        field = self._get_field(key) or self._add_field(key, Schema())
        if subkey:
            if isinstance(field, Schema):
                return field.__getitem__(subkey)
            raise TypeError("Field is not a schema: %s" % field._ref_path)
        return field

    def __setitem__(self, name: str, value: SchemaField) -> BaseField:
        '''
        :returns: field, equivalent to ``setattr(schema, key)``, however his method handles
            setting  nested values. For example:

            .. code-block:: python

                >>> schema = Schema()
                >>> schema.x = Schema()
                >>> schema['x.y'] = IntField(default=10)
                >>> print(schema.x.y)
                IntField(key='y', ...)
        '''
        key, _, subkey = name.partition('.')
        field = self._get_field(key) or self._add_field(key, Schema())
        if subkey:
            if isinstance(field, Schema):
                return field.__setitem__(subkey, value)
            raise TypeError("Field is not a schema: %s" % field._ref_path)

        return self._add_field(name, value)

    def _validate(self, config: 'Config', collect_errors: bool = False) -> List[ValidationError]:
        '''
        Validate the configuration by running any registered validators against it.

        :param config: config to validate
        '''
        if not self._is_feature_enabled(config):
            return []

        ignore_types = (IncludeFieldMixin, VirtualFieldMixin, InstanceMethodFieldMixin)
        errors = []

        for field in self._fields.values():
            if isinstance(field, ignore_types):
                continue

            try:
                self._validate_field(config, field)
            except ValidationError as err:
                if not collect_errors:
                    raise
                errors.append(err)
            except Exception as err:  # pylint: disable=broad-except
                exc = ValidationError(config, field, err)
                if not collect_errors:
                    raise exc from err
                errors.append(exc)

        for validator in self._validators:
            try:
                validator(config)
            except ValidationError as err:
                if not collect_errors:
                    raise
                errors.append(err)
            except Exception as err:  # pylint: disable=broad-except
                exc = ValidationError(config, None, err)
                if not collect_errors:
                    raise exc from err
                errors.append(exc)

        return errors

    def _validate_field(self, config: 'Config', field: BaseField) -> None:
        '''
        Validate a single field in the configuration.

        :param config: configuration
        :param field: the field to validate
        '''
        val = field.__getval__(config)
        if isinstance(field, Field):
            field.validate(config, val)
        elif isinstance(val, Config):
            val.validate()

    def get_all_fields(self) -> List[Tuple[str, 'Schema', BaseField]]:
        '''
        **(Deprecated, will be removed in v1.0.0)** get all the fields in the configuration. Use
        :meth:`~cincoconfig.get_all_fields`.

        :returns: a list of tuples with ``(key, schema, field)``
        '''
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .support import get_all_fields
        warnings.warn("Config.get_all_fields() is deprecated and will be removed in v1.0.0, use "
                      "cincoconfig.get_all_fields() instead.", DeprecationWarning)
        return get_all_fields(self)

    def generate_argparse_parser(self, **parser_kwargs) -> ArgumentParser:
        '''
        **(Deprecated, will be removed in v1.0.0)** generate an :class:`~argparse.ArgumentParser`
        for the schema. Use :meth:`~cincoconfig.generate_argparse_parser`.

        :returns: an ``ArgumentParser`` containing arguments that match the schema's fields
        '''
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .support import generate_argparse_parser
        warnings.warn("Schema.generate_argparse_parser() is deprecated and will be removed in "
                      "v1.0.0, use  cincoconfig.generate_argparse_parser instead.",
                      DeprecationWarning)
        return generate_argparse_parser(self, **parser_kwargs)

    def instance_method(self, key: str) -> Callable[['Config'], None]:
        '''
        **(Deprecated, will be removed in v1.0.0)** decorator to register an instance method with
        the schema. Use :meth:`~cincoconfig.instance_method`.
        '''
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .fields import instance_method
        warnings.warn("Schema.instance_method() is deprecated and will be removed in v1.0.0, use "
                      "cincoconfig.instance_method() instead.", DeprecationWarning)
        return instance_method(self, key)

    def validator(self, func: ConfigValidator) -> ConfigValidator:
        '''
        **(Deprecated, will be removed in v1.0.0)** decorator to register a validator method with
        the schema. Use :meth:`~cincoconfig.validator`.
        '''
        warnings.warn("Schema.validator() is deprecated and will be removed in v1.0.0, use "
                      "cincoconfig.validator() instead.", DeprecationWarning)
        self._validators.append(func)
        return func

    def make_type(self, name: str, module: str = None,
                  key_filename: str = None) -> Type['ConfigType']:
        '''
        **(Deprecated, will be removed in v1.0.0)** create a new type from the schema. Use
        :meth:`~cincoconfig.make_type`.
        '''
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .support import make_type
        warnings.warn("Schema.make_type() is deprecated and will be removed in v1.0.0, use "
                      "cincoconfig.make_type() instead.", DeprecationWarning)
        return make_type(self, name, module, key_filename)


class Config:  # pylint: disable=too-many-instance-attributes
    '''
    A configuration.

    Parsing and serializing the configuration is done via an intermediary object, a tree
    (:class:`dict`) containing only basic (serializable) values (see Field
    :meth:`~cincoconfig.abc.Field.to_basic`).

    When saving, the config will convert the current config values to a tree and then pass the
    tree to the specified format. When loading, the file content's will be passed to the formatter,
    which will return a basic tree that the config will validate and convert to actual config
    values.

    The initial config will be populated with default values, specified in each Field's *default*
    value. If the configuration needs to be initialized programmatically, prior to loading from a
    file, the :meth:`load_tree` method can be used to load a basic tree.

    .. code-block:: python

        schema = Schema()
        schema.port = PortField()
        schema.host = HostnameField()

        config = schema()
        # We didn't specify any default values, load from a dict

        config.load_tree({
            'port': 8080,
            'host': '127.0.0.1'
        })

        # Loading an initial tree above is essentially equivalent to:
        #
        # schema = Schema()
        # schema.port = PortField(default=8080)
        # schema.host = HostnameField(default='127.0.0.1')
        # config = schema()

    Each config object can have an associated :class:`cincoconfig.KeyFile`, passed in the
    constructor as ``key_filename``. If the configuration file doesn't have a key file path set,
    the config object will use the parent config's key file. Requesting a key file will bubble up
    to the first config object that has the key filename set and, if no config has a keyfile, the
    default path will be used, :const:`DEFAULT_CINCOKEY_FILEPATH`.
    '''
    DEFAULT_CINCOKEY_FILEPATH = os.path.join(os.path.expanduser("~"), ".cincokey")

    def __init__(self, schema: Schema, parent: 'Config' = None, key_filename: str = None, **data):
        '''
        :param schema: backing schema, stored as *_schema*
        :param parent: parent config instance, only set when this config is a field of another
            config, stored as *_parent*
        :param key_filename: path to key file
        :param data: configuration values
        '''
        self._schema = schema
        self._parent = parent
        self._container: Optional[ContainerValueMixin] = None
        self._data: Dict[str, Any] = OrderedDict()
        self._fields: Dict[str, BaseField] = OrderedDict()
        self._key = schema._key
        self.__keyfile = None  # type: Optional[KeyFile]

        if key_filename:
            self._key_filename = key_filename

        for key, value in data.items():
            self._set_value(key, value)

        for key, field in schema._fields.items():
            if key in data:
                continue

            field.__setdefault__(self)

    @property
    def _key_filename(self) -> str:
        '''
        :return: the path to the cinco encryption key file (if not set, get the parent config's
            key filename)
        '''
        if self.__keyfile:
            return self.__keyfile.filename
        if self._parent:
            return self._parent._key_filename
        return Config.DEFAULT_CINCOKEY_FILEPATH

    @_key_filename.setter
    def _key_filename(self, key_filename: str) -> None:
        '''
        Set the cinco encryption key file
        :param key_filename: path to the cinco encryption key file
        '''
        if not key_filename:
            self.__keyfile = None
        else:
            self.__keyfile = KeyFile(key_filename)

    @property
    def _keyfile(self) -> KeyFile:
        '''
        :returns: the config's encryption key file (if not set, get the parent config's key file)
        '''
        if not self.__keyfile:
            if self._parent:
                # This will bubble up to the root config
                self.__keyfile = self._parent._keyfile
            else:
                self.__keyfile = KeyFile(Config.DEFAULT_CINCOKEY_FILEPATH)
        return self.__keyfile

    def _get_field(self, key: str) -> Optional[BaseField]:
        '''
        :returns: a field from the schema or the dynamically added field if the schema is dynamic.
        '''
        return self._schema._get_field(key) or self._fields.get(key)

    def _set_value(self, key: str, value: Any) -> Any:
        '''
        Set a configuration value. This method passes the value through the field validation chain
        and then calls the target field's :meth:`~cincoconfig.abc.Field.__setval__` to actually
        set the value.

        Any exception that is raised by the field validation will be wrapped in an
        :class:`~cincoconfig.abc.ValidationError` and raised again.

        :param name: field key
        :param value: value to validate and set
        :raises ValidationError: setting the value failed
        '''
        field = self._get_field(key)
        if not field:
            if not self._schema._dynamic:
                raise AttributeError(key)
            field = self._fields[key] = AnyField()
            field.__setkey__(self._schema, key)

        if isinstance(field, Field):
            try:
                value = field.validate(self, value)
            except ValidationError:
                raise
            except Exception as err:
                raise ValidationError(self, field, err) from err
            else:
                field.__setval__(self, value)
                return value

        if isinstance(value, Config):
            value._parent = self
            value._key = key
        elif isinstance(value, dict) and isinstance(field, (Schema, ConfigTypeField)):
            # both Schema and ConfigTypeField implement __call__, which will return a Config object
            cfg = field(self)
            cfg._key = key
            cfg.load_tree(value)  # load_tree will raise a ValidationError on error
            value = cfg
        else:
            raise ValidationError(self, field,
                                  "Unable to coerce %s to Config" % type(value).__name__)

        self._data[key] = value
        return value

    def __setattr__(self, name: str, value: Any) -> Any:
        '''
        Validate a configuration value and set it.

        :param name: field key
        :param value: value
        '''
        if name.startswith("_"):
            return object.__setattr__(self, name, value)

        return self._set_value(name, value)

    def __getattr__(self, name: str) -> Any:
        '''
        Retrieve a config value.

        :param name: field key
        '''
        return self._get_value(name)

    def _get_value(self, key: str) -> Any:
        field = self._get_field(key)
        if not field and not self._schema._dynamic:
            raise AttributeError(key)

        return field.__getval__(self) if field else None

    def __getitem__(self, key: str) -> Any:
        '''
        :returns: field value, equivalent to ``getattr(config, key)``, however his method handles
            retrieving nested values. For example:

            .. code-block:: python

                >>> schema = Schema()
                >>> schema.x.y = IntField(default=10)
                >>> config = schema()
                >>> print(config['x.y'])
                10
        '''
        key, _, subkey = key.partition('.')
        value = self._get_value(key)
        return value.__getitem__(subkey) if subkey else value

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        return ((key, self._get_value(key)) for key in self._data)

    def __setitem__(self, key: str, value: Any) -> Any:
        '''
        Set a field value, equivalent to ``setattr(config, key)``, however this method handles
        setting nested values. For example:

        .. code-block:: python

            >>> schema = Schema()
            >>> schema.x.y = IntField(default=10)
            >>> config = schema()
            >>> config['x.y'] = 20
            >>> print(config.x.y)
            20
        '''
        key, _, subkey = key.partition('.')
        if subkey:
            return self._get_value(key).__setitem__(subkey, value)

        return self._set_value(key, value)

    def __contains__(self, key: str) -> bool:
        '''
        Check if key is in the configuration. This method handles checking nested values. For
        example:

        .. code-block:: python

                >>> schema = Schema()
                >>> schema.x.y = IntField(default=10)
                >>> config = schema()
                >>> 'x.y' in config
                True
        '''
        key, _, subkey = key.partition('.')
        if subkey:
            cfg = self._data.get(key)
            if isinstance(cfg, Config):
                return cfg.__contains__(subkey)
            return False

        return key in self._data

    @property
    def full_path(self) -> str:
        '''
        **(Deprecated, will be removed in v1.0.0)** get the full path to the configuration
        :returns: the full path to this configuration
        '''
        warnings.warn("Config.full_path is deprecated and will be removed in v1.0.0, use "
                      "cincoconfig.item_ref_path() instead", DeprecationWarning)
        return self._ref_path

    @property
    def _ref_path(self) -> str:
        '''
        :returns: the full reference path to the configuration
        '''
        if self._parent:
            root = self._parent._ref_path
        elif self._schema._schema:
            root = self._schema._schema._ref_path
        else:
            root = ''

        if root:
            path = root + "." + self._key
        else:
            path = self._key

        if self._container:
            try:
                pos = self._container._get_item_position(self)
            except:
                pos = ''
            else:
                if pos not in ('', None):
                    path += "[%s]" % pos

        return path

    def save(self, filename: str, format: str):
        '''
        Save the configuration to a file.

        :param filename: destination file path
        :param format: output format
        '''
        content = self.dumps(format)
        filename = os.path.expanduser(filename)
        with open(filename, 'wb') as file:
            file.write(content)

    def dumps(self, format: str, virtual: bool = False, sensitive_mask: str = None,
              **kwargs) -> bytes:
        '''
        Serialize the configuration to a string with the specified format.

        :param format: output format
        :param virtual: include virtual fields in the output
        :param sensitive_mask: replace secure values, see :meth:`to_tree`
        :param kwargs: additional keyword arguments to pass to the formatter's ``__init__()``
        :returns: serialized configuration file content
        '''
        formatter = ConfigFormat.get(format, **kwargs)
        return formatter.dumps(self, self.to_tree(virtual=virtual, sensitive_mask=sensitive_mask))

    def to_tree(self, virtual: bool = False, sensitive_mask: str = None) -> dict:
        '''
        Convert the configuration values to a tree.

        The *sensitive_mask* parameter is an optional string that will replace sensitive values in
        the tree.

        - ``None`` (default) - include the value as-is in the tree
        - ``len(sensitive_mask) == 1`` (single character) - replace every character with the
          ``sensitive_mask`` character. ``value = sensitive_mask * len(value)``
        - ``len(sensitive_mask) != 1`` (empty or multicharacter string) - replace the entire value
          with the ``sensitive_mask``.

        :param virtual: include virtual field values in the tree
        :param sensitive_mask: mask secure values with a string
        :returns: the basic tree containing all set values
        '''
        tree = {}
        fields: Dict[str, BaseField] = dict(self._schema._fields)
        fields.update(self._fields)

        for key, field in fields.items():
            is_virtual = virtual and isinstance(field, VirtualFieldMixin)
            if key not in self._data and not is_virtual:
                continue

            if isinstance(field, InstanceMethodFieldMixin):
                continue

            field_value = field.__getval__(self)
            value: Any = None

            if isinstance(field_value, Config):
                value = field_value.to_tree(virtual=virtual, sensitive_mask=sensitive_mask)
            elif isinstance(field, Field) and field.sensitive and sensitive_mask is not None:
                if not field_value:
                    pass
                elif len(sensitive_mask) == 1:
                    value = sensitive_mask * len(str(field_value))
                else:
                    value = sensitive_mask
            elif isinstance(field, Field):
                try:
                    value = field.to_basic(self, field_value)
                except ValidationError:
                    raise
                except Exception as err:
                    raise ValidationError(self, field, err) from err

            tree[key] = value

        return tree

    def load_tree(self, tree: dict, validate: bool = True) -> None:
        '''
        Load a tree and then validate the values.

        :param tree: a basic value tree
        '''
        for key, value in tree.items():
            field = self._get_field(key)
            if isinstance(field, Field):
                if isinstance(field.env, str) and field.env and os.environ.get(field.env):
                    continue

                try:
                    value = field.to_python(self, value)
                except ValidationError:
                    raise
                except Exception as err:
                    raise ValidationError(self, field, err) from err

            self._set_value(key, value)

        if validate:
            self.validate()

    def load(self, filename: str, format: str):
        '''
        Load the configuration from a file.

        :param filename: source filename
        :param format: source format
        '''
        filename = os.path.expanduser(filename)
        with open(filename, 'rb') as file:
            content = file.read()

        return self.loads(content, format)

    def loads(self, content: Union[str, bytes], format: str, **kwargs):
        '''
        Load a configuration from a str or bytes and process any
        :class:`~cincoconfig.IncludeField`.

        :param content: configuration content
        :param format: content format
        :param kwargs: additional keyword arguments to pass to the formatter's ``__init__()``
        '''
        if isinstance(content, str):
            content = content.encode()

        format_factory = partial(ConfigFormat.get, format, **kwargs)
        formatter = format_factory()

        tree = formatter.loads(self, content)
        tree = self._process_includes(self._schema, tree, format_factory)

        self.load_tree(tree)

    def _process_includes(self, schema: Schema, tree: dict,
                          format_factory: 'TFormatFactory') -> dict:
        '''
        Process include fields when loading when a configuration file. This method will load
        included fields for all ``IncludeField`` instances in the schema and all children schemas.

        :param schema: schema to load from
        :param tree: parsed tree
        :param format: config format
        '''
        sub_schemas = [(key, field) for key, field in schema._fields.items()
                       if isinstance(field, Schema)]
        includes: List[Tuple[str, IncludeFieldMixin]] = [
            (key, field) for key, field in schema._fields.items()  # type: ignore
            if isinstance(field, IncludeFieldMixin)
        ]
        for key, field in includes:
            # For each of the included field names, check if it has a value in the parsed tree
            # and, if it does, load the included file and combine it with the existing tree.
            filename = tree.get(key)
            if filename is None:
                continue

            # All included config files must have the same file format (you can't include XML from
            # a JSON file, for example).
            formatter = format_factory()
            tree = field.include(self, formatter, filename, tree)

        for key, sub_schema in sub_schemas:
            if tree.get(key):
                tree[key] = self._process_includes(sub_schema, tree[key], format_factory)

        return tree

    def validate(self, collect_errors: bool = False) -> List[ValidationError]:
        '''
        Perform validation on the entire config.
        '''
        return self._schema._validate(self, collect_errors=collect_errors)

    def cmdline_args_override(self, args: Namespace, ignore: Union[str, List[str]] = None) -> None:
        '''
        **(Deprecated, will be removed in v1.0.0)** override configuration values from the command
        line arguments. Use :meth:`~cincoconfig.cmdline_args_override`.

        :param args: parsed arguments
        :param ignore: list of field keys to ignore
        '''
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .support import cmdline_args_override
        warnings.warn("Schema.cmdline_args_override() is deprecated and will be removed in "
                      "v1.0.0, use cincoconfig.cmdline_args_override() instead",
                      DeprecationWarning)
        cmdline_args_override(self, args, ignore)


class ConfigType(Config):
    '''
    A base class for configuration types. A subclass of ``ConfigType`` is returned by the
    :meth:`~cincoconfig.make_type` function.
    '''
    __schema__ = None  # type: Schema
    __key_filename__ = None  # type: str

    def __init__(self, parent: Config = None, **kwargs):
        '''
        :param parent: parent configuration
        '''
        super().__init__(self.__schema__, parent, key_filename=self.__key_filename__, **kwargs)

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        if other.__class__ is not self.__class__:
            return False

        return self._data == other._data


class ConfigFormat:
    '''
    The base class for all configuration file formats.
    '''
    __registry: Dict[str, Type['ConfigFormat']] = {}
    __initialized: bool = False

    @classmethod
    def register(cls, name: str, format_cls: Type['ConfigFormat']) -> None:
        '''
        Register a new configuration format.

        :param name: format name
        :param format_cls: ``ConfigFormat`` subclass to register
        '''
        cls.__registry[name] = format_cls

    @classmethod
    def get(cls, name: str, **kwargs) -> 'ConfigFormat':
        '''
        Get a registered configuration format.

        :param name: config format name
        :param kwargs: keyword arguments to pass into the config format ``__init__()`` method
        :returns: the config format instance
        '''
        if not cls.__initialized:
            cls.initialize_registry()

        format_cls = cls.__registry[name]
        return format_cls(**kwargs)  # type: ignore

    @classmethod
    def initialize_registry(cls) -> None:
        '''
        Initialize the format registry for built-in formats.
        '''
        if cls.__initialized:
            return

        from .formats import FORMATS  # pylint: disable=cyclic-import, import-outside-toplevel
        for name, format_cls in FORMATS:
            cls.__registry[name] = format_cls

        cls.__initialized = True

    def dumps(self, config: Config, tree: dict) -> bytes:
        '''
        Convert the configuration value tree to a bytes object. This method is called to serialize
        the configuration to a buffer and eventually write to a file.

        :param config: current configuration
        :param tree: basic value tree, as returned by the Config
            :meth:`~cincoconfig.core.Config.to_tree` method.
        :returns: the serialized configuration
        '''
        raise NotImplementedError()

    def loads(self, config: Config, content: bytes) -> dict:
        '''
        Parse the serialized configuration to a basic value tree that can be parsed by the
        Config :meth:`~cincoconfig.core.Config.load_tree` method.

        :param config: current config
        :param content: serialized content
        :returns: the parsed basic value tree
        '''
        raise NotImplementedError()
