#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Union, Any
from .abc import Field

__all__ = ('Config', "ConfigGroup")


class Config:
    '''
    The base config object implements the set and get attribute magic

    Private class
    '''

    def __init__(self, key: str = None):
        self._key = key
        self._fields = {}

    def __setattr__(self, name, value):
        if name[0] == '_':
            object.__setattr__(self, name, value)
        else:
            self._fields[name] = value
            if isinstance(value, Field):
                value._key = name

    def __getattr__(self, name):
        value = self._fields.get(name)
        if value is None:
            value = self._fields[name] = Config(name)
        return value

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

    def compile(self):
        return ParsedConfig(self)


class ParsedConfig:

    def __init__(self, schema: Config, parent: 'ParsedConfig' = None, **kwargs):
        self._schema = schema
        self._data = dict()
        self._parent = parent

        for field in schema._fields.values():
            if isinstance(field, Config):
                value = ParsedConfig(field, parent=self)
            else:
                value = field.default
            self._data[field._key] = value

        for name, value in kwargs.items():
            self.__setattr__(name, value)

    def _get_field(self, name: str) -> Union[Field, 'ParsedConfig']:
        return self._schema._fields.get(name)

    def __setattr__(self, name: str, value: Any):
        if name[0] == '_':
            object.__setattr__(self, name, value)
            return

        field = self._get_field(name)
        if not field:
            raise AttributeError('%s field does not exist' % name)

        if isinstance(field, ParsedConfig):
            if not isinstance(value, dict):
                raise TypeError('ParsedConfig value must be a dict object')

            value = ParsedConfig(field._schema, **value)
            value.validate()
        else:
            value = field.validate(self, value)
        self._data[name] = value

    def __getattr__(self, name: str):
        field = self._get_field(name)
        if not field:
            raise AttributeError('%s field does not exist' % name)

        return self._data[name]

    def save(self, filename, format: str):
        # TODO
        pass

    def load(self, filename, format: str):
        pass

    def dumps(self, format: str):
        # TODO
        pass

    def loads(self, data: Union[str, bytes], format: str):
        # TODO
        pass

    @property
    def cinco_tree(self):
        d = {}
        for key, value in self._data.items():
            if isinstance(value, ParsedConfig):
                d[key] = value.cinco_tree
            else:
                d[key] = value  # Not handling special types right now...this is just a demo

        return d
