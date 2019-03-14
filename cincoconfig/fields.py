#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import os
import re
from ipaddress import IPv4Address, IPv4Network
from urllib.parse import urlparse
from typing import Union, List, Callable
from .abc import Field


__all__ = ('StringField', 'IntField', 'FloatField', 'PortField', 'IPv4AddressField',
           'IPv4NetworkField', 'FilenameField', 'BoolField', 'UrlField', 'AnyField', 'ListField',
           'HostnameField', 'DictField')


class StringField(Field):

    def __init__(self, *, min_len: int = None, max_len: int = None, regex: str = None,
                 choices: List[str] = None, case_sensitive: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.min_len = min_len
        self.max_len = max_len
        self.regex = re.compile(regex) if regex else None
        self.choices = choices
        self.case_sensitive = case_sensitive

    def _validate(self, cfg, value):
        if self.min_len is not None and len(value) < self.min_len:
            raise ValueError('%s must be at least %d characters' % (self.name, self.min_len))

        if self.max_len is not None and len(value) > self.max_len:
            raise ValueError('%s must not be more than %d chatacters' % (self.name, self.max_len))

        if self.regex and not self.regex.match(value):
            raise ValueError('%s does not match pattern %s' % (self.name, self.regex.pattern))

        if self.choices:
            valid = False
            if self.case_sensitive:
                valid = value in self.choices
            else:
                valid = value.lower() in [item.lower() for item in self.choices]

            if not valid:
                raise ValueError('%s is not a valid choice' % self.name)

        return value


class NumberField(Field):

    def __init__(self, type_cls, *, min: Union[int, float] = None, max: Union[int, float] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.type_cls = type_cls
        self.min = min
        self.max = max

    def _validate(self, cfg, value):
        try:
            value = self.type_cls(value)
        except:
            raise ValueError('%s is not a valid %s' % (self.name, self.type_cls.__name__))

        if self.min is not None and value < self.min:
            raise ValueError('%s must be >= %s' % (self.name, self.min))

        if self.max is not None and value > self.max:
            raise ValueError('%s must be <= %s' % (self.name, self.max))

        return value


class IntField(NumberField):

    def __init__(self, **kwargs):
        super().__init__(int, **kwargs)


class FloatField(NumberField):

    def __init__(self, **kwargs):
        super().__init__(float, **kwargs)


class PortField(IntField):

    def __init__(self, **kwargs):
        kwargs.setdefault('min', 1)
        kwargs.setdefault('max', 65535)
        super().__init__(**kwargs)


class IPv4AddressField(StringField):

    def _validate(self, cfg, value):
        try:
            _ = IPv4Address(value)
        except:
            raise ValueError('%s must be a valid IPv4 address' % self.name)
        return value


class IPv4NetworkField(StringField):

    def _validate(self, cfg, value):
        try:
            _ = IPv4Network(value)
        except:
            raise ValueError('%s must be a valid IPv4 Network (CIDR notation)' % self.name)
        return value


class HostnameField(StringField):

    def __init__(self, *, allow_ipv4: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.allow_ipv4 = allow_ipv4

    def _validate(self, cfg, value):
        # TODO
        return value


class FilenameField(StringField):

    def __init__(self, *, exists: Union[bool, str] = None, startdir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.exists = exists
        self.startdir = startdir

    def _validate(self, cfg, value):
        if not os.path.isabs(value):
            value = os.path.abspath(os.path.join(self.startdir, value))

        if os.path.sep == '\\':
            value = value.repalce('/', '\\')

        value_exists = os.path.exists(value)
        if self.exists is True and not value_exists:
            raise ValueError('%s file or directory does not exist' % self.name)
        elif self.exists is False and value_exists:
            raise ValueError('%s file or directory already exists' % self.name)
        elif self.exists == 'dir' and not os.path.isdir(value):
            raise ValueError('%s directory %s' %
                             (self.name, 'already exists' if value_exists else 'does not exist'))
        elif self.exists == 'file' and not os.path.isfile(value):
            raise ValueError('%s file %s' %
                             (self.name, 'already exists' if value_exists else 'does not exist'))

        return value


class BoolField(Field):

    def _validate(self, cfg, value):
        if isinstance(value, (int, float)):
            value = bool(value)
        elif isinstance(value, str):
            if value.lower() in ('t', 'true', '1', 'on', 'yes', 'y'):
                value = True
            elif value.lower() in ('f', 'false', '0', 'off', 'no', 'n'):
                value = False
            else:
                raise ValueError('%s is not a valid boolean' % self.name)
        elif not isinstance(value, bool):
            raise ValueError('%s is not a valid boolean' % self.name)


class UrlField(StringField):

    def _validate(self, cfg, value):
        try:
            _ = urlparse(value)
        except:
            raise ValueError('%s is not a valid URL' % self.name)
        return value


class ListField(Field):

    def __init__(self, field_cls, **kwargs):
        super().__init__(**kwargs)
        self.field_cls = field_cls

    def _validate(self, cfg, value):
        if self.required and len(value) == 0:
            raise ValueError('%s is required' % self.name)

        # TODO
        return value


class VirtualField(Field):
    # TODO
    pass


class AnyField(Field):
    # TODO
    pass


class DictField(Field):
    # TODO
    pass

