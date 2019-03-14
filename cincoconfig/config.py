#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Union, Any
from .abc import Field

__all__ = ('Config', "ConfigGroup")


class BaseConfig:
    '''
    The base config object implements the set and get attribute magic

    Private class
    '''

    def __init__(self, key: str = None):
        print('BaseConfig:', key)
        self._key = key
        self._fields = {}

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._fields[name] = value
            if isinstance(value, Field):
                value._key = name

    def __getattr__(self, name):
        value = self._fields.get(name)
        if value is None:
            value = self._fields[name] = ConfigGroup(name)
        return value

    def to_json(self):
        '''
        Wrote this method for testing/demo - will go away
        TODO: Remove and do this in formats/json.py
        '''
        d = {}
        for key, value in self._fields.items():
            if isinstance(value, ConfigGroup):
                d[key] = value.to_json()
            else:
                d[key] = value  # Not handling special types right now...this is just a demo

        return d


class Config(BaseConfig):
    '''
    The main config class that the user creates
    '''

    def __call__(self, **kwargs):
        return ParsedConfig(self, **kwargs)


class ConfigGroup(BaseConfig):
    '''
    Class for any sub-fields in the config
    '''
    pass


class ParsedConfig:

    def __init__(self, schema: Union[Config, ConfigGroup], **kwargs):
        self._schema = schema
        self._data = dict()

        for field in schema._fields.values():
            if isinstance(field, ConfigGroup):
                value = ParsedConfig(field)
            else:
                value = field.default
            self._data[field._key] = value

        for name, value in kwargs.items():
            self.__setattr__(name, value)

    def _get_field(self, name: str) -> Union[Field, ConfigGroup]:
        return self._schema._fields.get(name)

    def __setattr__(self, name: str, value: Any):
        if name.startswith('_'):
            super().__setattr__(name, value)
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
            value = field.validate(value)
        self._data[name] = value

    def __getattr__(self, name: str):
        field = self._get_field(name)
        if not field:
            raise AttributeError('%s field does not exist' % name)

        return self._data[name]

    def to_json(self):
        d = {}
        for key, value in self._data.items():
            if isinstance(value, ParsedConfig):
                d[key] = value.to_json()
            else:
                d[key] = value  # Not handling special types right now...this is just a demo

        return d
