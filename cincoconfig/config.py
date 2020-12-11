#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import sys
from typing import Union, Any, Iterator, Tuple, Callable, List
from argparse import Namespace
from itertools import chain
from .abc import Field, BaseConfig, BaseSchema, SchemaField, AnyField, ValidationError
from .fields import IncludeField, InstanceMethodField, VirtualField
from .formats import FormatRegistry, TFormatFactory


__all__ = ('Config', 'Schema')

ConfigValidator = Callable[['Config'], None]
ConfigInstanceMethod = Callable[['BaseConfig'], Any]


class Schema(BaseSchema):
    '''
    A config schema containing all available configuration options.

    A schema's fields and hierarchy are built dynamically.

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
    __initialized = False

    def __post_init__(self) -> None:
        '''
        Initialize the schema.
        '''
        self._validators = []  # type: List[ConfigValidator]
        self.__initialized = True

    def __setattr__(self, name: str, value: SchemaField):
        '''
        :param name: attribute name
        :param value: field or schema to add to the schema
        '''
        # if name[0] == '_':
        if not self.__initialized or name in self.__dict__:
            object.__setattr__(self, name, value)
        else:
            self._add_field(name, value)

    def get_all_fields(self) -> List[Tuple[str, 'Schema', SchemaField]]:
        '''
        Get all the fields and nested fields of the schema, including the nested schemas.

        .. code-block:: python

            >>> schema = Schema()
            >>> schema.x = IntField()
            >>> schema.y.z = StringField()
            >>> schema.z = StringField()
            >>> schema.get_all_fields()
            [
                ('x', schema, schema.x),
                ('y.z', schema.y, schema.y.z),
                ('z', schema, schema.z)
            ]

        The returned list of tuples have three values:

        1. `path` - the full path to the field.
        2. `schema` - the schema that the field belongs to.
        3. `field` - the field.

        The order of the fields will be the same order in which the fields were added to the
        schema.

        :returns: all the fields as a list of tuples: ``(path, schema, field)``
        '''
        ret = []
        prefix = self._key + '.' if self._key else ''
        for key, field in self._fields.items():
            ret.append((prefix + key, self, field))
            if isinstance(field, Schema):
                ret.extend([(prefix + subkey, schema, subfield)
                            for subkey, schema, subfield in field.get_all_fields()])
        return ret

    def __getitem__(self, key: str) -> SchemaField:
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

    def __getattr__(self, name: str) -> SchemaField:
        '''
        Retrieve a field by key or create a new ``Schema`` if the field doesn't exist.

        :param name: field or schema key
        '''
        field = self._fields.get(name)
        if field is None:
            field = self._fields[name] = Schema(name)
        return field

    def __iter__(self) -> Iterator[Tuple[str, SchemaField]]:
        '''
        Iterate over schema fields, produces as a list of tuples ``(key, field)``.
        '''
        for key, field in self._fields.items():
            yield key, field

    def __call__(self) -> 'Config':
        '''
        Compile the schema into an initial config with default values set.
        '''
        return Config(self)

    def make_type(self, name: str, module: str = None, key_filename: str = None) -> type:
        '''
        Create a new type that wraps this schema. This method should only be called once per
        schema object.

        Use this method when to create reusable configuration objects that can be used multiple
        times  in code in a more traditional Pythonic manner. For example, consider the following:

        .. code-block:: python

            item_schema = Schema()
            item_schema.url = UrlField()
            item_schema.verify_ssl = BoolField(default=True)

            schema = Schema()
            schema.endpoints = ListField(item_schema)

            config = schema()

            # to create new web hook items
            item = webhook_schema()
            item.url = 'https://google.com'
            item.verify_ssl = False

            config.endpoints.append(item)

        This is a cumbersome design when creating these objects within code. ``make_type`` will
        dynamically create a new class that can be used in a more Pythonic way:

        .. code-block:: python

            # same schema as above
            config = schema()
            Item = item_schema.make_type('Item')

            item = Item(url='https://google.com', verify_ssl=False)
            config.endpoints.append(item)

        The new class inherits from :class:`Config`.

        :param name: the new class name
        :param module: the owning module
        :param key_filename: the key file name passed to each new config object,
        :param validator: config validator callback method
        :returns: the new type
        '''
        schema = self

        def init_method(self, **kwargs):
            Config.__init__(self, schema, key_filename=key_filename)
            for key, value in kwargs.items():
                self.__setattr__(key, value)

        init_method.__name__ = '__init__'
        result = type(name, (ConfigType,), {
            '__init__': init_method,
            '__schema__': schema,
        })
        # This is copied from the namedtuple method. We try to set the module of the new
        # class to the calling module.
        if module is None:
            try:
                module = sys._getframe(1).f_globals.get('__name__', '__main__')
            except (AttributeError, ValueError):  # pragma: no cover
                pass
        if module is not None:
            result.__module__ = module

        return result

    def validator(self, func: ConfigValidator) -> ConfigValidator:
        '''
        Decorator to register a new validator with the schema. All validators will be run against
        the configuration whenever the configuration is loaded from disk. Multiple validators can
        be registered by using the decorator multiple times. Subconfigs can also be validated by
        using the decorateor on the sub schema.

        .. code-block:: python

            schema = Schema()
            schema.x = IntField()
            schema.y = IntField()
            schema.db.username = StringField()
            schema.db.password = StringField()

            @schema.validator
            def validate_x_lt_y(cfg):
                if cfg.x and cfg.y and cfg.x >= cfg.y:
                    raise ValueError('x must be less-than y')

            @schema.db.validator
            def validate_db_creds(cfg):
                if cfg.username and not db.password:
                    raise ValueError('db.password is required when username is specified')

            config = schema()
            config.load('mycfg.json', format='json')  # will call the above validators
            # .....

        The validator function needs to raise an exception, preferably a :class:`ValueError`, if
        the validation fails.

        :param func: validator function that accepts a single argument: :class:`Config`.
        :returns: ``func``
        '''
        self._validators.append(func)
        return func

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

    def _validate_field(self, config: 'Config', field: SchemaField) -> None:
        if isinstance(field, InstanceMethodField):
            return

        if isinstance(field, Field):
            val = field.__getval__(config)
            field.validate(config, val)
        elif isinstance(field, Schema):
            field._validate(config[field._key])  # type: ignore

    def instance_method(self, key: str) -> Callable:
        '''
        Bind an instance method to all configurations. This is a convenience method that adds a
        :class:`~cincoconfig.fields.InstanceMethodField` to the schema. The instance method is
        called with the signature ``(config, *args, **kwargs)``, where ``config`` is the instance
        config object.

        Use this decorator like this:

        .. code-block:: python

            schema = Schema()

            @schema.instance_method('test')
            def test(cfg, x, y, z=None):
                # do stuff
                pass

            config = schema()
            config.test(1, y=2)

        This decorator is especially useful when creating new configuration types through the
        :meth:`~Config.make_type`.

        :param key: instance method name
        :returns: the decorated method
        '''
        def wrapper(meth: ConfigInstanceMethod) -> ConfigInstanceMethod:
            self._add_field(key, InstanceMethodField(meth))
            return meth
        return wrapper


class Config(BaseConfig):
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
    __initialized = False

    def __init__(self, schema: BaseSchema, parent: 'Config' = None, key_filename: str = None):
        '''
        :param schema: backing schema, stored as *_schema*
        :param parent: parent config instance, only set when this config is a field of another
            config, stored as *_parent*
        :param key_filename: path to key file
        '''
        super().__init__(schema, parent, key_filename)

        self.__initialized = True

        for key, field in schema._fields.items():
            if isinstance(field, BaseSchema):
                value = Config(field, parent=self)
                self._data[key] = value
            else:
                field.__setdefault__(self)

    def __setattr__(self, name: str, value: Any):
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
        # if name[0] == '_':
        if not self.__initialized or name in self.__dict__:
            object.__setattr__(self, name, value)
            return

        field = self._get_field(name)
        if not field:
            # if the schema is dynamic then we allow adding fields to the _fields dict
            # _add_field will raise an exception if the schema is not dynamic
            field = self._add_field(name, AnyField())

        if isinstance(field, BaseSchema):
            if isinstance(value, Config):
                cfg = value
                cfg._parent = self
            elif not isinstance(value, dict):
                raise TypeError('Config value must be a dict object')
            else:
                cfg = Config(field, parent=self)
                cfg.load_tree(value)

            self._data[name] = cfg
        else:
            try:
                field.__setval__(self, value)
            except ValidationError:
                raise
            except Exception as err:
                raise ValidationError(self, field, err) from err

    def __getattr__(self, name: str) -> Any:
        '''
        Retrieve a config value.

        :param name: field key
        '''
        field = self._get_field(name)
        if not field:
            if not self._schema._dynamic:
                raise AttributeError('%s field does not exist' % name)

            # if we are dynamic then return None and don't raise an exception
            return None

        if isinstance(field, BaseSchema):
            return self._data[name]

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
            return getattr(self, key).__getitem__(remainder)
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any):
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
            getattr(self, key).__setitem__(remainder, value)
        else:
            setattr(self, key, value)

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

    def save(self, filename: str, format: str):
        '''
        Save the configuration to a file.

        :param filename: destination file path
        :param format: output format
        '''
        content = self.dumps(format)
        with open(filename, 'wb') as file:
            file.write(content)

    def load(self, filename: str, format: str):
        '''
        Load the configuration from a file.

        :param filename: source filename
        :param format: source format
        '''

        with open(filename, 'rb') as file:
            content = file.read()

        return self.loads(content, format)

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
        formatter = FormatRegistry.get(format, **kwargs)
        return formatter.dumps(self, self.to_tree(virtual=virtual, sensitive_mask=sensitive_mask))

    def _process_includes(self, schema: BaseSchema, tree: dict,
                          format_factory: TFormatFactory) -> dict:
        '''
        Process include fields when loading when a configuration file. This method will load
        included fields for all ``IncludeField`` instances in the schema and all children schemas.

        :param schema: schema to load from
        :param tree: parsed tree
        :param format: config format
        '''
        sub_schemas = [(key, field) for key, field in schema._fields.items()
                       if isinstance(field, BaseSchema)]
        includes = [(key, field) for key, field in schema._fields.items()
                    if isinstance(field, IncludeField)]
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

        format_factory = FormatRegistry.make_factory(format, **kwargs)
        formatter = format_factory()

        tree = formatter.loads(self, content)
        tree = self._process_includes(self._schema, tree, format_factory)

        self.load_tree(tree)

    def cmdline_args_override(self, args: Namespace, ignore: Union[str, List[str]] = None) -> None:
        '''
        Override configuration setting based on command line arguments, parsed from the
        :mod:`argparse` module. This method is useful when loading a configuration but allowing the
        user the option to override or extend the configuration via command line arguments.

        .. code-block:: python

            parser = argparse.ArgumentParser()
            parser.add_argument('-d', '--debug', action='store_const', const='debug', dest='mode')
            parser.add_argument('-p', '--port', action='store', dest='http.port')
            parser.add_argument('-H', '--host', action='store', dest='http.address')
            parser.add_argument('-c', '--config', action='store')

            args = parser.parse_args()
            if args.config:
                config.load(args.config, format='json')

            config.cmdline_args_override(args, ignore=['config'])

            # cmdline_args_override() is equivalent to doing:

            if args.mode:
                config.mode = args.mode
            if getattr(args, 'http.port'):
                config.http.port = getattr(args, 'http.port')
            if getattr(args, 'http.address'):
                config.http.address = getattr(args, 'http.address')

        :param args: parsed command line arguments from :meth:`~argparse.ArgumentParser.parse_args`
        :param ignore: list of arguments to ignore and not process
        '''
        if isinstance(ignore, str):
            ignore = [ignore]
        else:
            ignore = ignore or []

        for key, value in vars(args).items():
            if key not in ignore and value is not None:
                self.__setitem__(key, value)

    def load_tree(self, tree: dict) -> None:
        '''
        Load a tree and then validate the values.

        :param tree: a basic value tree
        '''
        for key, value in tree.items():
            field = self._get_field(key)
            if isinstance(field, Field):
                value = field.to_python(self, value)

            self.__setattr__(key, value)

        self.validate()

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        '''
        Iterate over the configuration values as ``(key, value)`` tuples.
        '''
        for key, field in chain(self._schema._fields.items(), self._fields.items()):
            if isinstance(field, Field):
                value = field.__getval__(self)
            else:
                value = self._data[key]
            yield key, value

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
            is_virtual = virtual and isinstance(field, VirtualField)
            if key not in self._data and not is_virtual:
                continue

            if isinstance(field, BaseSchema):
                value = self._data[key].to_tree(virtual=virtual, sensitive_mask=sensitive_mask)
            elif field.sensitive and sensitive_mask is not None:
                value = self._data[key]
                if not value:
                    pass
                elif len(sensitive_mask) == 1:
                    value = sensitive_mask * len(value)
                else:
                    value = sensitive_mask
            else:
                value = field.to_basic(self, field.__getval__(self))

            tree[key] = value

        return tree

    def validate(self) -> None:
        '''
        Perform validation on the entire config.
        '''
        self._schema._validate(self)  # type: ignore


class ConfigType(Config):
    __schema__ = None  # type: Schema
