#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Abstract base classes.
'''

import os
from typing import Any, Callable, Union, Optional, Dict

from .encryption import KeyFile

SchemaField = Union['BaseSchema', 'Field']


class Field:
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
    '''
    storage_type = Any

    def __init__(self, *, name: str = None, key: str = None, required: bool = False,
                 default: Union[Callable, Any] = None,
                 validator: Callable[['BaseConfig', Any], Any] = None):
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
        '''
        self._name = name or None
        self.key = key or ''
        self.required = required
        self._default = default
        self.validator = validator

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
        return self._name or self.key

    def _validate(self, cfg: 'BaseConfig', value: Any) -> Any:
        '''
        Subclass validation hook. The default implementation just returns ``value`` unchanged.
        '''
        return value

    def validate(self, cfg: 'BaseConfig', value: Any) -> Any:
        '''
        Start the validation chain and verify that the value is specified if *required=True*.

        :param cfg: current config
        :param value: value to validate
        :returns: the validated value
        '''
        if self.required and value is None:
            raise ValueError('%s is required' % self.name)

        if value is None:
            return value

        value = self._validate(cfg, value)
        if self.validator:
            value = self.validator(cfg, value)

        return value

    def __setval__(self, cfg: 'BaseConfig', value: Any):
        '''
        Set the validated value in the config. The default implementation passes the value through
        the validation chain and then set's the validated value int the config.

        :param cfg: current config
        :param value: value to validated
        '''
        cfg._data[self.key] = self.validate(cfg, value)

    def __getval__(self, cfg: 'BaseConfig') -> Any:
        '''
        Retrieve the value from the config. The default implementation retrieves the value from the
        config by the field *key*.

        :param cfg: current config
        :returns: the value stored in the config
        '''
        return cfg._data[self.key]

    def __setkey__(self, schema: 'BaseSchema', key: str):
        '''
        Set the field's *key*, which is called when the field is added to a schema. The default
        implementation just sets ``self.key = key``

        :param schema: the schema the field belongs to
        :param key: the field's unique key
        '''
        self.key = key

    def __setdefault__(self, cfg: 'BaseConfig'):
        '''
        Set the default value of the field in the config. This is called when the config is first
        created.

        :param cfg: current config
        '''
        cfg._data[self.key] = self.default

    def to_python(self, cfg: 'BaseConfig', value: Any) -> Any:
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

    def to_basic(self, cfg: 'BaseConfig', value: Any) -> Any:
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


class BaseSchema:
    '''
    Base schema that holds the list of fields in the *_fields* attributes.

    :ivar str _key: schema key
    :ivar bool _dynamic: the schema is dynamic
    :ivar dict _fields: registered fields
    '''
    storage_type = 'BaseSchema'

    def __init__(self, key: str = None, dynamic: bool = False):
        '''
        :param key: the schema key, only used for sub-schemas, and stored in the instance as
            *_key*
        :param dynamic: the schema is dynamic and can contain fields not originally specified in
            the schema and stored in the instance as *_dynamic*
        '''
        self._key = key
        self._dynamic = dynamic
        self._fields = dict()  # type: Dict[str, SchemaField]
        self.__post_init__()

    def __post_init__(self) -> None:
        '''
        Subclass hook that is called at the end of ``__init__``. This allows subclasses to perform
        additional initialization without overriding the ``__init__`` method. The default
        implementation does nothing.
        '''

    def __setkey__(self, parent: 'BaseSchema', key: str) -> None:
        '''
        Field protocol, set the schema *_key* attribute.
        '''
        self._key = key

    def _add_field(self, key: str, field: SchemaField) -> SchemaField:
        '''
        Add a field to the schema. This method will call ``field.__setkey__(self, key)``.

        :returns: the added field (``field``)
        '''
        self._fields[key] = field
        if isinstance(field, (Field, BaseSchema)):
            field.__setkey__(self, key)
        return field

    def _get_field(self, key: str) -> Optional[SchemaField]:
        '''
        :returns: the field identified by *key*, if it exists in the schema
        '''
        return self._fields.get(key)


class BaseConfig(BaseSchema):
    '''
    Base configuration that holds configuration values in the *_data* attribute. Each base config
    object can have an associated :class:`cincoconfig.KeyFile`, passed in the
    constructor as ``key_filename``. If the configuration file doesn't have a key file path set,
    the config object will use the parent config's key file. Requesting a key file will bubble up
    to the first config object that has the key filename set and, if no config has a keyfile, the
    default path will be used, :const:`DEFAULT_CINCOKEY_FILEPATH`.

    :ivar dict _data: currently set configuration values
    :ivar dict _fields: dynamically added fields (not in *_schema*)
    :ivar BaseSchema _schema: backing schema
    :ivar BaseConfig _parent: parent configuration
    '''

    #: Default file path to the cincokey file (``~/.cincokey``). This value is dereferenced on first
    #: access so you can modify this value for the entire cincoconfig installation
    DEFAULT_CINCOKEY_FILEPATH = os.path.join(os.path.expanduser("~"), ".cincokey")

    def __init__(self, schema: BaseSchema, parent: 'BaseConfig' = None,
                 key_filename: str = None):
        '''
        :param schema: backing schema
        :param parent: parent configuration, when this object is a sub configuration
        :param key_filename: path to cinco key file
        '''
        super().__init__()
        self._schema = schema
        self._parent = parent
        self._data = dict()  # type: Dict[str, Any]
        self.__keyfile = None  # type: Optional[KeyFile]

        if key_filename:
            self._key_filename = key_filename

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
        return BaseConfig.DEFAULT_CINCOKEY_FILEPATH

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
                self.__keyfile = KeyFile(BaseConfig.DEFAULT_CINCOKEY_FILEPATH)
        return self.__keyfile

    def _add_field(self, key: str, field: SchemaField) -> SchemaField:
        '''
        Attempt to add a new field to the configuration. This method only works when the backing
        schema is dynamic, otherwise a :class:`TypeError` will be raised.

        :param key: field key
        :param field: field to add
        :returns: the added field
        :raises TypeError: the configuration is not dynamic and new fields cannot be added
        '''
        if not self._schema._dynamic:
            raise TypeError('unrecgonized configuration field: %s' % key)
        return super()._add_field(key, field)

    def _get_field(self, key: str) -> Optional[SchemaField]:
        '''
        :returns: the field identified by *key*
        '''
        return self._schema._get_field(key) or super()._get_field(key)

    def validate(self) -> None:
        '''
        Validate the configuration. The default implementation does nothing.
        '''


class ConfigFormat:
    '''
    The base class for all configuration file formats.
    '''

    def dumps(self, config: BaseConfig, tree: dict) -> bytes:
        '''
        Convert the configuration value tree to a bytes object. This method is called to serialize
        the configuration to a buffer and eventually write to a file.

        :param config: current configuration
        :param tree: basic value tree, as returned by the Config
            :meth:`~cincoconfig.config.Config.to_tree` method.
        :returns: the serialized configuration
        '''
        raise NotImplementedError()

    def loads(self, config: BaseConfig, content: bytes) -> dict:
        '''
        Parse the serialized configuration to a basic value tree that can be parsed by the
        Config :meth:`~cincoconfig.config.Config.load_tree` method.

        :param config: current config
        :param content: serialized content
        :returns: the parsed basic value tree
        '''
        raise NotImplementedError()
