#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Union, Any, Iterator, Tuple, Callable
from itertools import chain
from .abc import Field, BaseConfig, BaseSchema, SchemaField, AnyField
from .fields import IncludeField
from .formats import FormatRegistry


__all__ = ('Config', 'Schema')

ConfigValidator = Callable[['Config'], None]


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

    def __setattr__(self, name: str, value: SchemaField):
        '''
        :param name: attribute name
        :param value: field or schema to add to the schema
        '''
        if name[0] == '_':
            object.__setattr__(self, name, value)
        else:
            self._add_field(name, value)

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

    def __call__(self, validator: ConfigValidator = None) -> 'Config':
        '''
        Compile the schema into an initial config with default values set.
        '''
        return Config(self, validator=validator)


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

    def __init__(self, schema: BaseSchema, parent: 'Config' = None,
                 validator: ConfigValidator = None):
        '''
        :param schema: backing schema, stored as *_schema*
        :param parent: parent config instance, only set when this config is a field of another
            config, stored as *_parent*
        '''
        super().__init__(schema, parent)
        self._validator = validator

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

        :param name: field key
        :param value: value to validate and set
        '''
        if name[0] == '_':
            object.__setattr__(self, name, value)
            return

        field = self._get_field(name)
        if not field:
            # if the schema is dynamic then we allow adding fields to the _fields dict
            # _add_field will raise an exception if the schema is not dynamic
            field = self._add_field(name, AnyField())

        if isinstance(field, BaseSchema):
            if not isinstance(value, dict):
                raise TypeError('Config value must be a dict object')

            cfg = self._data[name] = Config(field, parent=self)
            cfg.load_tree(value)
        else:
            field.__setval__(self, value)

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

    def dumps(self, format: str, **kwargs) -> bytes:
        '''
        Serialize the configuration to a string with the specified format.

        :param format: output format
        :param kwargs: additional keyword arguments to pass to the formatter's ``__init__()``
        :returns: serialized configuration file content
        '''
        # formatter = FormatRegistry.get(format, **kwargs)
        formatter = FormatRegistry.get(format, **kwargs)
        return formatter.dumps(self, self.to_tree())

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

        formatter = FormatRegistry.get(format, **kwargs)

        tree = formatter.loads(self, content)

        # Process includes
        # Get the include fields in the backing schema
        includes = [(key, field) for key, field in self._schema._fields.items()
                    if isinstance(field, IncludeField)]
        for key, field in includes:
            # For each of the included field names, check if it has a value in the parsed tree
            # and, if it does, load the included file and combine it with the existing tree.
            filename = tree.get(key)
            if filename is None:
                continue

            # All included config files must have the same file format (you can't include XML from
            # a JSON file, for example).
            formatter = FormatRegistry.get(format, **kwargs)
            tree = field.include(self, formatter, filename, tree)

        self.load_tree(tree)

    def load_tree(self, tree: dict):
        '''
        Load a tree and then validate the values.

        :param tree: a basic value tree
        '''
        for key, value in tree.items():
            field = self._get_field(key)
            if isinstance(field, Field):
                value = field.to_python(self, value)

            self.__setattr__(key, value)

        if self._validator:
            self._validator(self)

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

    def to_tree(self) -> dict:
        '''
        Convert the configuration values to a tree.

        :returns: the basic tree containing all set values
        '''
        tree = {}
        fields = dict(self._schema._fields)
        fields.update(self._fields)

        for key, field in fields.items():
            if isinstance(field, BaseSchema):
                tree[key] = self._data[key].to_tree()
            elif key in self._data:
                tree[key] = field.to_basic(self, field.__getval__(self))

        return tree
