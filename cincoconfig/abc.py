#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Any, Callable


class Field:

    def __init__(self, *, name: str = None, key: str = None, required: bool = False,
                 default: Any = None, validator: Callable = None):
        self._name = name or None
        self.key = key or None
        self.required = required
        self._default = default
        self.validator = validator

    @property
    def default(self):
        return self._default() if callable(self._default) else self._default

    @property
    def name(self):
        return self._name or self.key

    def _validate(self, cfg, value):
        return value

    def validate(self, cfg, value):
        if self.required and value is None:
            raise ValueError('%s is required' % self.name)

        if value is None:
            return value

        value = self._validate(cfg, value)
        if self.validator:
            value = self.validator(cfg, value)

        return value

    def __setval__(self, cfg, value):
        cfg._data[self.key] = self.validate(cfg, value)

    def __getval__(self, cfg):
        return cfg._data[self.key]

    def __setkey__(self, cfg, name):
        self.key = name

    def __setdefault__(self, cfg):
        cfg._data[self.key] = self.default

    def to_python(self, cfg, value):
        '''
        Convert the basic value to a Python value.
        '''
        return value

    def to_basic(self, cfg, value):
        '''
        Convert the Python value to the basic value.
        '''
        return value


class AnyField(Field):
    pass


class ConfigFormat:
    pass
