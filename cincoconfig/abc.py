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
        self._key = key or None
        self.required = required
        self._default = default
        self.validator = validator

    @property
    def default(self):
        return self._default() if callable(self._default) else self._default

    @property
    def name(self):
        return self._name or self.key

    def set_default(self, cfg):
        value = self.default if not callable(self.default) else self.default()
        cfg.set(self.name, value)

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


class ConfigFormat:
    pass
