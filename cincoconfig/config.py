#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Union, Any
from .abc import Field, ConfigFormat
from . import formats


__all__ = ('Config', "ConfigGroup")


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
            self._fields[name] = value
            if isinstance(value, Field):
                value.__setkey__(self, name)

    def __getattr__(self, name):
        field = self._fields.get(name)
        if field is None:
            field = self._fields[name] = Schema(name)
        return field

    def to_json(self):
        '''
        Wrote this method for testing/demo - will go away
        TODO: Remove and do this in formats/json.py
        '''
        d = {}
        for key, value in self._fields.items():
            if isinstance(value, Config):
                d[key] = value.to_json()
            else:
                d[key] = value  # Not handling special types right now...this is just a demo

        return d

    def __call__(self, **kwargs):
        return Config(self)


class Config:

    def __init__(self, schema: Schema, parent: 'Config' = None):
        self._schema = schema
        self._data = dict()
        self._parent = parent

        for name, field in schema._fields.items():
            if isinstance(field, Schema):
                value = Config(field, parent=self)
                self._data[name] = value
            else:
                field.__setdefault__(self)

    def __setattr__(self, name: str, value: Any):
        if name[0] == '_':
            object.__setattr__(self, name, value)
            return

        field = self._schema._fields.get(name)
        if not field:
            if not self._schema._dynamic:
                raise AttributeError('%s field does not exist' % name)
            self._data[name] = value
            return

        if isinstance(field, Schema):
            if not isinstance(value, dict):
                raise TypeError('ParsedConfig value must be a dict object')

            cfg = self._data[name] = Config(field._schema)
            cfg.load_tree(value)
        else:
            field.__setval__(self, value)

    def __getattr__(self, name: str):
        field = self._schema._fields.get(name)
        if not field:
            if not self._schema._dynamic:
                raise AttributeError('%s field does not exist' % name)
            else:
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
        with open(filename, mode) as fp:
            fp.write(content)

    def load(self, filename: Union[str, dict], format: str = None):
        if isinstance(filename, dict):
            return self._load_tree(filename)

        with open(filename, 'rb') as fp:
            content = fp.read()

        self.loads(content, format)

    def dumps(self, format: str):
        formatter = self._get_format(format)
        return formatter.dumps(self._schema, self._to_tree())

    def loads(self, content: Union[str, bytes], format: str):
        formatter = self._get_format(format)

        if formatter.is_binary and isinstance(content, str):
            content = content.encode()
        elif not formatter.is_binary and isinstance(content, bytes):
            content = content.decode()

        tree = formatter.loads(self._schema, content)
        self.load_tree(tree)

    def _get_format(self, format: str) -> ConfigFormat:
        fmt = format.lower()
        if fmt == 'json':
            cls = formats.JsonConfigFormat
        elif fmt == 'yaml':
            cls = formats.YamlConfigFormat
        elif fmt == 'ini':
            cls = formats.IniConfigFormat
        elif fmt == 'xml':
            cls = formats.XmlConfigFormat
        else:
            raise ValueError('unknown format: %s' % format)

        return cls()

    def load_tree(self, tree: dict):
        for key, field in tree.items():
            self.__setattr__(key, field)

    def _to_tree(self):
        d = {}
        for key, field in self._schema._fields.items():
            if isinstance(field, Schema):
                d[key] = self._data[key]._to_tree()
            else:
                d[key] = field.__getval__(self)

        return d
