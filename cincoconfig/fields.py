#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import os
import re
import socket
from ipaddress import IPv4Address, IPv4Network
from urllib.parse import urlparse
from typing import Union, List, Type, Any
from .abc import Field, AnyField


__all__ = ('StringField', 'IntField', 'FloatField', 'PortField', 'IPv4AddressField',
           'IPv4NetworkField', 'FilenameField', 'BoolField', 'UrlField', 'AnyField', 'ListField',
           'HostnameField', 'DictField', 'AnyField')


class StringField(Field):

    def __init__(self, *, min_len: int = None, max_len: int = None, regex: str = None,
                 choices: List[str] = None, transform_case: str = None,
                 transform_strip: Union[bool, str] = None, **kwargs):
        super().__init__(**kwargs)
        self.min_len = min_len
        self.max_len = max_len
        self.regex = re.compile(regex) if regex else None
        self.choices = choices
        self.transform_case = transform_case.lower() if transform_case else None
        self.transform_strip = transform_strip

        if self.transform_case and self.transform_case not in ('lower', 'upper'):
            raise TypeError('transform_case must be "lower" or "upper"')

    def _validate(self, cfg, value):
        if self.transform_strip:
            if isinstance(self.transform_strip, str):
                value = value.strip(self.transform_strip)
            else:
                value = value.strip()

        if self.transform_case:
            value = value.lower() if self.transform_case == 'lower' else value.upper()

        if self.min_len is not None and len(value) < self.min_len:
            raise ValueError('%s must be at least %d characters' % (self.name, self.min_len))

        if self.max_len is not None and len(value) > self.max_len:
            raise ValueError('%s must not be more than %d chatacters' % (self.name, self.max_len))

        if self.regex and not self.regex.match(value):
            raise ValueError('%s does not match pattern %s' % (self.name, self.regex.pattern))

        if self.choices and value not in self.choices:
            raise ValueError('%s is not a valid choice' % self.name)

        return value


class LogLevelField(StringField):

    def __init__(self, levels: List[str] = None, **kwargs):
        if not levels:
            levels = ['debug', 'info', 'warning', 'error', 'critical']

        self.levels = levels
        kwargs.setdefault('transform_case', 'lower')
        kwargs.setdefault('transform_strip', True)
        kwargs['choices'] = levels
        super().__init__(**kwargs)


class ApplicationModeField(StringField):
    HELPER_MODE_PATTERN = re.compile('^[a-zA-Z0-9_]+$')

    def __init__(self, modes: List[str] = None, create_helpers: bool = True, **kwargs):
        if not modes:
            modes = ['development', 'production']

        self.modes = modes
        self.create_helpers = create_helpers

        if create_helpers:
            for mode in modes:
                if not self.HELPER_MODE_PATTERN.match(mode):
                    raise TypeError('invalid mode name: %s' % mode)

        kwargs.setdefault('transform_case', 'lower')
        kwargs.setdefault('transform_strip', True)
        kwargs['choices'] = modes
        super().__init__(**kwargs)

    def _create_helper(self, mode):
        return VirtualField(lambda cfg: cfg[self.key] == mode)

    def __setkey__(self, schema, key):
        self.key = key
        if self.create_helpers:
            for mode in self.modes:
                schema._add_field('is_%s_mode' % mode, self._create_helper(mode))


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
            addr = IPv4Address(value)
        except:
            raise ValueError('%s must be a valid IPv4 address' % self.name)
        return str(addr)


class IPv4NetworkField(StringField):

    def _validate(self, cfg, value):
        try:
            net = IPv4Network(value)
        except:
            raise ValueError('%s must be a valid IPv4 Network (CIDR notation)' % self.name)
        return str(net)


class HostnameField(StringField):
    HOSTNAME_REGEX = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9.\-]+$')
    NETBIOS_REGEX = re.compile(r"^[\w!@#$%^()\-'{}\.~]{1,15}$")

    def __init__(self, *, allow_ipv4: bool = True, resolve: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.allow_ipv4 = allow_ipv4
        self.resolve = resolve

    def _validate(self, cfg, value):
        try:
            addr = IPv4Address(value)
        except:
            pass
        else:
            if self.allow_ipv4:
                return str(addr)
            raise ValueError('%s is not a valid DNS hostname')

        # value is a hostname
        if self.resolve:
            try:
                name = socket.gethostbyname(value)
            except:
                raise ValueError('%s DNS resolution failed' % self.name)
            else:
                return name

        dns_match = self.HOSTNAME_REGEX.match(value)
        nb_match = self.NETBIOS_REGEX.match(value)
        if not dns_match and not nb_match:
            raise ValueError('%s is not a valid hostname')

        return value


class FilenameField(StringField):

    def __init__(self, *, exists: Union[bool, str] = None, startdir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.exists = exists
        self.startdir = startdir

    def _validate(self, cfg, value):
        if not os.path.isabs(value) and self.startdir:
            value = os.path.abspath(os.path.join(self.startdir, value))

        if os.path.sep == '\\':
            value = value.replace('/', '\\')

        value_exists = os.path.exists(value)
        if self.exists is True and not value_exists:
            raise ValueError('%s file or directory does not exist' % self.name)
        if self.exists is False and value_exists:
            raise ValueError('%s file or directory already exists' % self.name)
        if self.exists == 'dir' and not os.path.isdir(value):
            raise ValueError('%s directory %s' %
                             (self.name, 'already exists' if value_exists else 'does not exist'))
        if self.exists == 'file' and not os.path.isfile(value):
            raise ValueError('%s file %s' %
                             (self.name, 'already exists' if value_exists else 'does not exist'))

        return value


class BoolField(Field):
    TRUE_VALUES = ('t', 'true', '1', 'on', 'yes', 'y')
    FALSE_VALUES = ('f', 'false', '0', 'off', 'no', 'n')

    def _validate(self, cfg, value):
        if isinstance(value, (int, float)):
            value = bool(value)
        elif isinstance(value, str):
            if value.lower() in self.TRUE_VALUES:
                value = True
            elif value.lower() in self.FALSE_VALUES:
                value = False
            else:
                raise ValueError('%s is not a valid boolean' % self.name)
        elif not isinstance(value, bool):
            raise ValueError('%s is not a valid boolean' % self.name)
        return value


class UrlField(StringField):

    def _validate(self, cfg, value):
        try:
            url = urlparse(value)
            if not url.scheme:
                raise ValueError('no scheme url scheme')
        except:
            raise ValueError('%s is not a valid URL' % self.name)
        return value


class ListFieldWrapper:

    def __init__(self, field: Type[Field], *items):
        self.field = field
        self._items = []
        for item in items:
            self.append(item)

    def __len__(self):
        return len(self._items)

    def __eq__(self, other: list):
        return self._items == other

    def __iter__(self):
        return iter(self._items)

    def append(self, item: Any):
        value = self.field.validate(item)
        self._items.append(value)

    def __add__(self, other: list):
        return self._items + other

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __getitem__(self, index: int):
        return self._items[index]

    def __delitem__(self, index: int):
        del self._items[index]

    def __setitem__(self, index: int, value: Any):
        self._items[index] = self.field.validate(value)

    def __hash__(self):
        return hash(self.field) + hash(self._items)

    def clear(self):
        self._items = []

    def copy(self):
        return ListFieldWrapper(self.field, *self._items)

    def count(self, value: Any):
        return self._items.count(value)

    def extend(self, other: list):
        for item in other:
            self.append(item)

    def index(self, value: Any):
        return self._items.index(value)

    def insert(self, index, value: Any):
        value = self.field.validate(value)
        self._items.insert(index, value)

    def pop(self, index: int = None):
        return self._items.pop(index)

    def remove(self, value: Any):
        value = self.field.validate(value)
        self._items.remove(value)

    def reverse(self):
        self._items.reverse()

    def sort(self, key=None, reverse=False):
        self._items.sort(key, reverse)


class ListField(Field):

    def __init__(self, field: Field = None, **kwargs):
        super().__init__(**kwargs)
        self.field = field

    def _validate(self, cfg, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError('%s is not a list object' % self.name)

        if self.required and not value:
            raise ValueError('%s is required' % self.name)

        if not self.field or isinstance(self.field, AnyField):
            return value

        value = ListFieldWrapper(self.field, *value)
        return value


class VirtualField(Field):

    def __init__(self, getter, **kwargs):
        super().__init__(**kwargs)
        self.getter = getter

    def __setdefault__(self, cfg):
        pass

    def __getval__(self, cfg):
        return self.getter(cfg)

    def __setval__(self, cfg, value):
        raise TypeError('%s is readonly' % self.key)


class DictField(Field):

    def _validate(self, cfg, value):
        if not isinstance(value, dict):
            raise ValueError('%s is not a dict object' % self.name)

        if self.required and not value:
            raise ValueError('%s is required' % self.name)

        return value
