#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Union, Any
from .abc import Field, AnyField
from .formats import FormatRegistry


__all__ = ('Config', 'Schema')


class Schema:
    '''
    The base config object implements the set and get attribute magic

    Private class
    '''

    def __init__(self, key: str = None, dynamic: bool = False):
        self._key = key
        self._dynamic = dynamic
        self._fields = {}

    def __setattr__(self, name, value):
        if name[0] == '_':
            object.__setattr__(self, name, value)
        else:
            self._add_field(name, value)

    def _add_field(self, key, field):
        self._fields[key] = field
        if isinstance(field, Field):
            field.__setkey__(self, key)

    def __getattr__(self, name):
        field = self._fields.get(name)
        if field is None:
            field = self._fields[name] = Schema(name)
        return field

    def __iter__(self):
        for key, field in self._fields.items():
            yield key, field

    def to_json(self):
        '''
        Wrote this method for testing/demo - will go away
        TODO: Remove and do this in formats/json.py
        '''
        data = {}
        for key, value in self._fields.items():
            if isinstance(value, Config):
                data[key] = value.to_json()
            else:
                data[key] = value  # Not handling special types right now...this is just a demo

        return data

    def __call__(self, **kwargs):
        return Config(self)


class Config:

    def __init__(self, schema: Schema, parent: 'Config' = None):
        self._schema = schema
        self._data = dict()
        self._dynamic_fields = dict() if self._schema._dynamic else None
        self._parent = parent

        for key, field in schema._fields.items():
            if isinstance(field, Schema):
                value = Config(field, parent=self)
                self._data[key] = value
            else:
                field.__setdefault__(self)

    def __setattr__(self, name: str, value: Any):
        if name[0] == '_':
            object.__setattr__(self, name, value)
            return

        field = self._get_field(name)
        if not field:
            if not self._schema._dynamic:
                raise AttributeError('%s field does not exist' % name)

            self._dynamic_fields = field = AnyField()
            field.__setkey__(self, name)

        if isinstance(field, Schema):
            if not isinstance(value, dict):
                raise TypeError('ParsedConfig value must be a dict object')

            cfg = self._data[name] = Config(field._schema)
            cfg.load_tree(value)
        else:
            field.__setval__(self, value)

    def __getattr__(self, name: str):
        field = self._get_field(name)
        if not field:
            if not self._schema._dynamic:
                raise AttributeError('%s field does not exist' % name)
            return None

        if isinstance(field, Schema):
            return self._data[name]

        return field.__getval__(self)

    def __getitem__(self, key: str):
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any):
        setattr(self, key, value)

    def save(self, filename: str, format: str):
        content = self.dumps(format)
        mode = 'wb' if isinstance(content, bytes) else 'w'
        with open(filename, mode) as file:
            file.write(content)

    def load(self, filename: Union[str, dict], format: str = None):
        if isinstance(filename, dict):
            return self._load_tree(filename)

        with open(filename, 'rb') as file:
            content = file.read()

        return self.loads(content, format)

    def dumps(self, format: str, **kwargs):
        formatter = FormatRegistry.get(format, **kwargs)
        return formatter.dumps(self._schema, self, self._to_tree())

    def loads(self, content: Union[str, bytes], format: str, **kwargs):
        formatter = FormatRegistry.get(format, **kwargs)

        if formatter.is_binary and isinstance(content, str):
            content = content.encode()
        elif not formatter.is_binary and isinstance(content, bytes):
            content = content.decode()

        tree = formatter.loads(self._schema, content)
        return self.load_tree(tree)

    def _get_field(self, key):
        field = self._schema._fields.get(key)
        if not field and self._dynamic_fields:
            field = self._dynamic_fields.get(key)
        return field

    def load_tree(self, tree: dict):
        for key, value in tree.items():
            field = self._get_field(key)
            if isinstance(field, Field):
                value = field.to_python(self, value)

            self.__setattr__(key, value)

    def __iter__(self):
        for key, field in self._schema:
            value = field.__getval__(self)
            yield key, value

        if self._dynamic_fields:
            for key, field in self._dynamic_fields:
                yield key, field.__getval__(self)

    def _to_tree(self):
        tree = {}
        fields = dict(self._schema._fields)
        if self._dynamic_fields:
            fields.update(self._dynamic_fields)

        for key, field in fields.items():
            if isinstance(field, Schema):
                tree[key] = self._data[key]._to_tree()
            elif key in self._data:
                tree[key] = field.to_basic(self, field.__getval__(self))

        return tree
