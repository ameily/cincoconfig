#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Cinco Config String Fields.
'''

import os
import re
import socket
from ipaddress import IPv4Address, IPv4Network
from urllib.parse import urlparse
from typing import Union, List
from cincoconfig.abc import Field
from cincoconfig.config import Config, Schema
from .primitives import VirtualField


__all__ = ('StringField', 'IPv4AddressField', 'IPv4NetworkField', 'FilenameField', 'UrlField',
           'HostnameField', 'ApplicationModeField', 'LogLevelField')


class StringField(Field):
    '''
    A string field.
    '''

    def __init__(self, *, min_len: int = None, max_len: int = None, regex: str = None,
                 choices: List[str] = None, transform_case: str = None,
                 transform_strip: Union[bool, str] = None, **kwargs):
        '''
        The string field can perform transformations on the value prior to validating it if either
        *transform_case* or *transform_strip* are specified.

        :param min_len: minimum allowed length
        :param max_len: maximum allowed length
        :param regex: regex pattern that the value must match
        :param choices: list of valid choices
        :param transform_case: transform the value's case to either ``upper`` or ``lower`` case
        :param transform_strip: strip the value by calling :meth:`str.strip`.
            Setting this to ``True`` will call :meth:`str.strip` without any arguments (ie.
            striping all whitespace characters) and if this is a ``str``, then :meth:`str.strip`
            will be called with ``transform_strip``.
        '''
        super().__init__(**kwargs)
        self.min_len = min_len
        self.max_len = max_len
        self.regex = re.compile(regex) if regex else None
        self.choices = choices
        self.transform_case = transform_case.lower() if transform_case else None
        self.transform_strip = transform_strip

        if self.transform_case and self.transform_case not in ('lower', 'upper'):
            raise TypeError('transform_case must be "lower" or "upper"')

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
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
    '''
    A field representing the Python log level.
    '''

    def __init__(self, levels: List[str] = None, **kwargs):
        '''
        :param levels: list of log levels. If not specified, the default Python log levels will be
            used: ``debug``, ``info``, ``warning``, ``error``, and ``critical``.
        '''
        if not levels:
            levels = ['debug', 'info', 'warning', 'error', 'critical']

        self.levels = levels
        kwargs.setdefault('transform_case', 'lower')
        kwargs.setdefault('transform_strip', True)
        kwargs['choices'] = levels
        super().__init__(**kwargs)


class ApplicationModeField(StringField):
    '''
    A field representing the application operating mode.
    '''
    HELPER_MODE_PATTERN = re.compile('^[a-zA-Z0-9_]+$')

    def __init__(self, modes: List[str] = None, create_helpers: bool = True, **kwargs):
        '''
        The *create_helpers* parameter will create a boolean :class:`VirtualField` for each
        ``mode`` named ``is_<mode>_mode``, that returns ``True`` when the mode is active. When
        *create_helpers=True* then each mode name must be a valid Python variable name.

        :param modes: application modes, if not specified the default modes will be used:
            ``production`` and ``development``
        :param create_helpers: create helper a bool ``VirtualField`` for each mode
        '''
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

    def _create_helper(self, mode: str) -> 'VirtualField':
        '''
        Create helper VirtualField.
        '''
        return VirtualField(lambda cfg: cfg[self.key] == mode)

    def __setkey__(self, schema: Schema, key: str):
        '''
        Set the key and optionally add ``VirtualField`` helpers to the schema if
        *create_helpers=True*.
        '''
        self.key = key
        if self.create_helpers:
            for mode in self.modes:
                schema._add_field('is_%s_mode' % mode, self._create_helper(mode))


class UrlField(StringField):
    '''
    A URL field. Values are validated that they are both a valid URL and contain a valid scheme.
    '''

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate the value.

        :param cfg: current config
        :param value: value to validate
        '''
        try:
            url = urlparse(value)
            if not url.scheme:
                raise ValueError('no scheme url scheme')
        except:
            raise ValueError('%s is not a valid URL' % self.name)
        return value


class IPv4AddressField(StringField):
    '''
    IPv4 address field.
    '''

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        try:
            addr = IPv4Address(value)
        except:
            raise ValueError('%s must be a valid IPv4 address' % self.name)
        return str(addr)


class IPv4NetworkField(StringField):
    '''
    IPv4 network field. This field accepts CIDR notation networks in the form of ``A.B.C.D/Z``.
    '''

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        try:
            net = IPv4Network(value)
        except:
            raise ValueError('%s must be a valid IPv4 Network (CIDR notation)' % self.name)
        return str(net)


class HostnameField(StringField):
    '''
    A field representing a network hostname or, optionally, a network address.
    '''
    HOSTNAME_REGEX = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9.\-]+$')
    NETBIOS_REGEX = re.compile(r"^[\w!@#$%^()\-'{}\.~]{1,15}$")

    def __init__(self, *, allow_ipv4: bool = True, resolve: bool = False, **kwargs):
        '''
        :param allow_ipv4: allow both a hostname and an IPv4 address
        :param resolve: resolve hostnames to their IPv4 address and raise a :class:`ValueError`
            if the resolution fails
        '''
        super().__init__(**kwargs)
        self.allow_ipv4 = allow_ipv4
        self.resolve = resolve

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to valdiate
        '''
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
            # resolve hostname to IPv4 address
            try:
                name = socket.gethostbyname(value)
            except:
                raise ValueError('%s DNS resolution failed' % self.name)
            else:
                return name

        # Validate that the value *looks* like a DNS hostname or Windows NetBios name
        dns_match = self.HOSTNAME_REGEX.match(value)
        nb_match = self.NETBIOS_REGEX.match(value)
        if not dns_match and not nb_match:
            raise ValueError('%s is not a valid hostname')

        return value


class FilenameField(StringField):
    '''
    A field for representing a filename on disk.
    '''

    def __init__(self, *, exists: Union[bool, str] = None, startdir: str = None, **kwargs):
        '''
        The *exists* parameter can be set to one of the following values:

        - ``None`` - don't check file's existance
        - ``False`` - validate that the filename does not exist
        - ``True`` - validate that the filename does exist
        - ``dir`` - validate that the filename is a directory that exists
        - ``file`` - validate that the filename is a file that exists

        The *startdir* parameter, if specified, will resolve filenames starting from a directory
        and will cause all filenames to be validated to their absolute file path. If not specified,
        filename's will be resolved relative to :meth:`os.getcwd` and the relative file path will
        be validated.

        :param exists: validate the filename's existence on disk
        :param startdir: resolve relative paths to a start directory
        '''
        super().__init__(**kwargs)
        self.exists = exists
        self.startdir = startdir

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''
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
