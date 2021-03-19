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

ConfigValidator = Callable[['Config'], None]
FieldValidator = Callable[['Config', Any], Any]
SchemaField = Union['Schema', 'Field', 'ConfigType']


class ValidationError(ValueError):

    def __init__(self, config: 'Config', field: Optional['SchemaField'], exc: Union[str, Exception],
                 full_path: str = None):
        super().__init__(config, field, exc, full_path)
        self.config = config
        self.field = field
        self.exc = exc
        self._full_path = full_path

    def __str__(self):
        if isinstance(self.exc, OSError):
            msg = self.exc.strerror
        else:
            msg = str(self.exc)

        path = self.full_path
        if self.field and self.field.name:
            path = "%s (%s)" % (self.field.name, path)

        return '%s: %s' % (path, msg)

    @property
    def full_path(self) -> str:
        return self._full_path or (self.field.full_path if self.field else self.config.full_path)


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
    pass


class InstanceMethodFieldMixin:
    pass


class IncludeFieldMixin:

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

    def __init__(self, key: str = None, name: str = None):
        self._key: str = ''
        self._name = name
        self._schema: Optional['Schema'] = None

    def __setkey__(self, schema: 'Schema', key: str) -> None:
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

    @property
    def full_path(self) -> str:
        path = [self._key]
        curr = self._schema
        while curr:
            path.append(curr._key)

        path.reverse()
        return '.'.join(path)


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

    The Field ``key`` is used to set and reference the value in the config.

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

    def __init__(self, *, key: str = None, name: str = None, required: bool = False,
                 default: Union[Callable, Any] = None, validator: FieldValidator = None,
                 sensitive: bool = False, description: str = None, help: str = None,
                 env: Union[bool, str] = None):
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
        :param sensitive: the field stores a senstive value
        :param help: the field documentation
        '''
        super().__init__(name=name, key=key)
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
        cfg._data[self._key] = self.validate(cfg, value)

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
        Set the field's *key*, which is called when the field is added to a schema. The default
        implementation just sets ``self.key = key``

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


class Schema(BaseField):

    def __init__(self, key: str = None, dynamic: bool = False, env: Union[str, bool] = None,
                 config_type: Type['ConfigType'] = None):
        super().__init__(key=key)
        self._dynamic = dynamic
        self._fields: Dict[str, BaseField] = OrderedDict()
        self._env_prefix = '' if env is True else env
        self._validators: List[ConfigValidator] = []
        self._config_type = config_type

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

    def _get_field(self, key: str) -> Optional[BaseField]:
        return self._fields.get(key)

    def __setattr__(self, name: str, value: Any) -> Any:
        '''
        :param name: attribute name
        :param value: field or schema to add to the schema
        '''
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        elif isinstance(value, BaseField) or isconfigtype(value):
            value = self._add_field(name, value)
        else:
            raise TypeError("TODO")

        return value

    def _add_field(self, name: str, field: SchemaField) -> BaseField:
        '''
        Add a field to the schema. This method will call ``field.__setkey__(self, key)``.

        :returns: the added field (``field``)
        '''
        if isconfigtype(field):
            field = Schema(config_type=field)  # type: ignore

        self._fields[name] = field  # type: ignore
        field.__setkey__(self, name)
        return field  # type: ignore

    def __getattr__(self, name: str) -> BaseField:
        '''
        Retrieve a field by key or create a new ``Schema`` if the field doesn't exist.

        :param name: field or schema key
        '''
        field = self._fields.get(name)
        if field is None:
            field = self._add_field(name, Schema())
        return field

    def __call__(self, **data):
        '''
        Compile the schema into an initial config with default values set.
        '''
        return Config(self, **data)

    def __iter__(self) -> Iterator[Tuple[str, BaseField]]:
        '''
        Iterate over schema fields, produces as a list of tuples ``(key, field)``.
        '''
        for key, field in self._fields.items():
            yield key, field

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
        field = self._fields[key]
        if subkey:
            if isinstance(field, Schema):
                return field[subkey]
            raise KeyError(subkey)
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
        if not isinstance(value, BaseField) and not isconfigtype(value):
            raise TypeError("TODO")

        key, _, subkey = name.partition('.')
        field = self._fields[key]
        if subkey:
            if isinstance(field, Schema):
                return field.__setitem__(subkey, value)
            raise KeyError(subkey)

        return self._add_field(name, value)

    def _validate(self, config: 'Config') -> None:
        '''
        Validate the configuration by running any registered validators against it.

        :param config: config to validate
        '''
        for field in self._fields.values():
            try:
                self._validate_field(config, field)
            except ValidationError:
                raise
            except Exception as err:
                raise ValidationError(config, field, err) from err  # type: ignore

        for validator in self._validators:
            validator(config)

    def _validate_field(self, config: 'Config', field: BaseField) -> None:
        if isinstance(field, Field):
            val = field.__getval__(config)
            field.validate(config, val)
        elif isinstance(field, Schema) and isinstance(config[field._key], Config):
            field._validate(config[field._key])

    def get_all_fields(self) -> List[Tuple[str, Schema, BaseField]]:
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .support import get_all_fields
        warnings.warn("Config.get_all_fields() is deprecated, use "
                      "cincoconfig.get_all_fields() instead.", DeprecationWarning)
        return get_all_fields(self)

    def generate_argparse_parser(self, **parser_kwargs) -> ArgumentParser:
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .support import generate_argparse_parser
        warnings.warn("Config.generate_argparse_parser() is deprecated, use "
                      "cincoconfig.generate_argparse_parser instead.", DeprecationWarning)
        return generate_argparse_parser(**parser_kwargs)

    def instance_method(self, key: str) -> Callable[['Config'], None]:
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .fields import instance_method
        warnings.warn("Config.instance_method() is deprecated, use "
                      "cincoconfig.instance_method() instead.", DeprecationWarning)
        return instance_method(self, key)


class Config:
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
    '''

    def __init__(self, schema: Schema, parent: 'Config' = None, key_filename: str = None, **data):
        '''
        :param schema: backing schema, stored as *_schema*
        :param parent: parent config instance, only set when this config is a field of another
            config, stored as *_parent*
        :param key_filename: path to key file
        '''
        self._schema = schema
        self._parent = parent
        self._container: Optional[ContainerValueMixin] = None
        self._data: Dict[str, Any] = OrderedDict()
        self._fields: Dict[str, BaseField] = OrderedDict()

        for key, value in data.items():
            self._set_value(key, value)

        for key, field in schema._fields.items():
            if key in data:
                continue

            if isinstance(field, Schema):
                self._data[key] = Config(field, self)
            elif isinstance(field, Field):
                field.__setdefault__(self)

    def _get_field(self, key: str) -> Optional[BaseField]:
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
                raise ValueError("ferp")
            field = self._fields[key] = AnyField()

        if isinstance(field, Field):
            try:
                value = field.validate(self, value)
            except Exception as err:
                raise ValidationError(self, field, err) from err
            else:
                self._data[key] = value
                return value

        if not isinstance(field, Schema):
            raise TypeError("TODO")

        if isinstance(value, Config):
            value._parent = self
        elif isinstance(value, dict):
            cfg = Config(field, parent=self)
            try:
                cfg.load_tree(value)
                cfg.validate()
            except ValidationError:
                raise
            except Exception as err:
                raise ValidationError(cfg, None, err) from err
            else:
                value = cfg
        else:
            raise ValidationError(self, field, ValueError("TODO"))

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
        field = self._get_field(name)
        if not field:
            if not self._schema._dynamic:
                raise AttributeError("TODO")
            return None

        return field.__getval__(self)

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
        if '.' in key:
            key, remainder = key.split('.', 1)
            return self.__getattr__(key).__getitem__(remainder)
        return self.__getattr__(key)

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
        if '.' in key:
            key, remainder = key.split('.', 1)
            self.__getattr__(key).__setitem__(remainder, value)
        else:
            self._set_value(key, value)

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
        if '.' in key:
            key, remainder = key.split('.', 1)
            cfg = self._data.get(key)
            if isinstance(cfg, Config):
                return cfg.__contains__(remainder)
            return False

        return key in self._data

    @property
    def full_path(self) -> str:
        '''
        :returns: the full path to this configuration
        '''
        if self._parent:
            path = self._parent.full_path + "." + self._schema._key
        else:
            path = self._schema.full_path

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

        The *sensitive_mask* parameter is an optional string that will repalce sensitive values in
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
        fields = dict(self._schema._fields)
        fields.update(self._fields)

        for key, field in fields.items():
            is_virtual = virtual and isinstance(field, VirtualFieldMixin)
            if key not in self._data and not is_virtual:
                continue

            if isinstance(field, InstanceMethodFieldMixin):
                continue

            if isinstance(field, Schema):
                value = self._data[key].to_tree(virtual=virtual, sensitive_mask=sensitive_mask)
            elif isinstance(field, Field) and field.sensitive and sensitive_mask is not None:
                value = self._data[key]
                if not value:
                    pass
                elif len(sensitive_mask) == 1:
                    value = sensitive_mask * len(value)
                else:
                    value = sensitive_mask
            elif isinstance(field, Field):
                try:
                    value = field.to_basic(self, field.__getval__(self))
                except ValidationError:
                    raise
                except Exception as err:
                    raise ValidationError(self, field, err) from err

            tree[key] = value

        return tree

    def load_tree(self, tree: dict) -> None:
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

            self.__setattr__(key, value)

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

    def validate(self):
        '''
        Perform validation on the entire config.
        '''
        self._schema._validate(self)

    def cmdline_args_override(self, args: Namespace, ignore: Union[str, List[str]] = None) -> None:
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .support import cmdline_args_override
        warnings.warn("Schema.cmdline_args_override() is deprecated, use "
                      "cincoconfig.cmdline_args_override() instead", DeprecationWarning)
        cmdline_args_override(self, args, ignore)


class ConfigType(Config):
    __schema__ = None  # type: Schema

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
    def register(cls, name: str, format_cls: Type['ConfigFormat']):
        cls.__registry[name] = format_cls

    @classmethod
    def get(cls, name: str, **kwargs) -> 'ConfigFormat':
        format_cls = cls.__registry[name]
        return format_cls(**kwargs)  # type: ignore

    @classmethod
    def initialize_registry(cls) -> None:
        '''
        Initialize the format reigstry for built-in formats.
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
            :meth:`~cincoconfig.config.Config.to_tree` method.
        :returns: the serialized configuration
        '''
        raise NotImplementedError()

    def loads(self, config: Config, content: bytes) -> dict:
        '''
        Parse the serialized configuration to a basic value tree that can be parsed by the
        Config :meth:`~cincoconfig.config.Config.load_tree` method.

        :param config: current config
        :param content: serialized content
        :returns: the parsed basic value tree
        '''
        raise NotImplementedError()


TFormatFactory = Callable[[], ConfigFormat]


def isconfigtype(obj: Any) -> bool:
    '''
    Check if an object is configuration type (is class and is subclass of :class:`BaseConfig`).

    :param obj: object to check
    :returns: the object is a configuration type
    '''
    return inspect.isclass(obj) and issubclass(obj, Config)


ConfigFormat.initialize_registry()
