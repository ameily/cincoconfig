#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Union, Any, Iterator, Tuple
from . import abc
# from .formats import FormatRegistry
from . import formats


__all__ = ('Config', 'Schema')


class Schema:
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

    def __init__(self, key: str = None, dynamic: bool = False):
        '''
        :param key: the schema key, only used for sub-schemas, and stored in the instance as
            *_key*
        :param dynamic: the schema is dynamic and can contain fields not originally specified in
            the schema and stored in the instance as *_dynamic*
        '''
        #: the schema key
        self._key = key
        #: the schema is dynamic
        self._dynamic = dynamic
        #: schema fields
        self._fields = {}

    def __setattr__(self, name: str, value: Union[abc.Field, 'Schema']):
        '''
        :param name: attribute name
        :param value: field or schema to add to the schema
        '''
        if name[0] == '_':
            object.__setattr__(self, name, value)
        else:
            self._add_field(name, value)

    def _add_field(self, key: str, field: Union[abc.Field, 'Schema']):
        '''
        Add a field to the schema. Calls :meth:`~cincoconfig.abc.Field.__setkey__` on the field
        after adding it to the schema.

        :param key: field key
        :param field: new field or schema
        '''

        self._fields[key] = field
        if isinstance(field, abc.Field):
            field.__setkey__(self, key)

    def __getattr__(self, name: str) -> Union[abc.Field, 'Schema']:
        '''
        Retrieve a field by key or create a new ``Schema`` if the field doesn't exist.

        :param name: field or schema key
        '''
        field = self._fields.get(name)
        if field is None:
            field = self._fields[name] = Schema(name)
        return field

    def __iter__(self) -> Iterator[Tuple[str, abc.Field]]:
        '''
        Iterate over schema fields, produces as a list of tuples ``(key, field)``.
        '''
        for key, field in self._fields.items():
            yield key, field

    def __call__(self, **kwargs) -> 'Config':
        '''
        Compile the schema into an initial config with default values set.
        '''
        return Config(self)


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

        # The above is essentially equivalent to:
        #
        # schema = Schema()
        # schema.port = PortField(default=8080)
        # schema.host = HostnameField(default='127.0.0.1')
        # config = schema()
    '''

    def __init__(self, schema: Schema, parent: 'Config' = None):
        '''
        :param schema: backing schema, stored as *_schema*
        :param parent: parent config instance, only set when this config is a field of another
            config, stored as *_parent*
        '''
        self._schema = schema
        self._parent = parent
        self._data = dict()
        self._dynamic_fields = dict() if self._schema._dynamic else None

        for key, field in schema._fields.items():
            if isinstance(field, Schema):
                value = Config(field, parent=self)
                self._data[key] = value
            else:
                field.__setdefault__(self)

    def _add_field(self, key: str, field: abc.Field = None) -> abc.Field:
        '''
        Add a field to the configuration. This method only works when the underlying schema is
        dynamic, otherwise an :class:`AttributeError` will be raised.

        :param key: field key
        :param field: field to add, if not specified the :class:`~cincoconfig.abc.AnyField` will be
            created
        :returns: the created field
        '''
        if not self._schema._dynamic:
            raise AttributeError('%s field does not exist' % key)

        field = field or abc.AnyField()
        self._fields[key] = field
        if isinstance(field, abc.Field):
            field.__setkey__(self, key)

        return field

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
            # if the schema is dynamic then we allow adding fields to the _dynamic_fields dict
            # _add_field will raise an exception if the schema is not dynamic
            field = self._add_field(name)

        if isinstance(field, Schema):
            if not isinstance(value, dict):
                raise TypeError('ParsedConfig value must be a dict object')

            cfg = self._data[name] = Config(field._schema, parent=self)
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

        if isinstance(field, Schema):
            return self._data[name]

        return field.__getval__(self)

    def __getitem__(self, key: str) -> Any:
        '''
        :returns: field value, equivalent to ``getattr(config, key)``
        '''
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any):
        '''
        Set a field value, equivalent to ``setattr(config, key)``.
        '''
        setattr(self, key, value)

    def save(self, filename: str, format: str):
        '''
        Save the configuration to a file.

        :param filename: destination file path
        :param format: output format
        '''
        content = self.dumps(format)
        mode = 'wb' if isinstance(content, bytes) else 'w'
        with open(filename, mode) as file:
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

    def dumps(self, format: str, **kwargs) -> Union[str, bytes]:
        '''
        Serialize the configuration to a string with the specified format.

        :param format: output format
        :param kwargs: additional keyword arguments to pass to the formatter's ``__init__()``
        :returns: serialized configuration file content
        '''
        # formatter = FormatRegistry.get(format, **kwargs)
        formatter = formats.FormatRegistry.get(format, **kwargs)
        return formatter.dumps(self._schema, self, self.to_tree())

    def loads(self, content: Union[str, bytes], format: str, **kwargs):
        '''
        Load a configuration from a str or bytes.

        :param content: configuration content
        :param format: content format
        :param kwargs: additional keyword arguments to pass to the formatter's ``__init__()``
        '''
        formatter = formats.FormatRegistry.get(format, **kwargs)

        if formatter.is_binary and isinstance(content, str):
            content = content.encode()
        elif not formatter.is_binary and isinstance(content, bytes):
            content = content.decode()

        tree = formatter.loads(self._schema, self, content)
        self.load_tree(tree)

    def _get_field(self, key: str) -> Union[abc.Field, Schema]:
        '''
        Get field by key.

        :param key: field key
        '''
        field = self._schema._fields.get(key)

        if not field and self._dynamic_fields:
            field = self._dynamic_fields.get(key)
        return field

    def load_tree(self, tree: dict):
        '''
        Load a tree and then validate the values.

        :param tree: a basic value tree
        '''
        for key, value in tree.items():
            field = self._get_field(key)
            if isinstance(field, abc.Field):
                value = field.to_python(self, value)

            self.__setattr__(key, value)

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        '''
        Iterate over the configuration values as ``(key, value)`` tuples.
        '''
        for key, field in self._schema:
            value = field.__getval__(self)
            yield key, value

        if self._dynamic_fields:
            for key, field in self._dynamic_fields:
                yield key, field.__getval__(self)

    def to_tree(self) -> dict:
        '''
        Convert the configuration values to a tree.

        :returns: the basic tree containing all set values
        '''
        tree = {}
        fields = dict(self._schema._fields)
        if self._dynamic_fields:
            fields.update(self._dynamic_fields)

        for key, field in fields.items():
            if isinstance(field, Schema):
                tree[key] = self._data[key].to_tree()
            elif key in self._data:
                tree[key] = field.to_basic(self, field.__getval__(self))

        return tree
