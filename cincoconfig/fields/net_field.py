#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Network fields
'''
import socket
import re
from ipaddress import IPv4Address, IPv4Network

from ..core import Config
from .number_field import IntField
from .string_field import StringField


class PortField(IntField):
    '''
    Network port field.
    '''
    storage_type = int

    def __init__(self, **kwargs):
        kwargs.setdefault('min', 1)
        kwargs.setdefault('max', 65535)
        super().__init__(**kwargs)


class IPv4AddressField(StringField):
    '''
    IPv4 address field.
    '''
    storage_type = str

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        value = super()._validate(cfg, value)

        try:
            addr = IPv4Address(value)
        except ValueError as err:
            raise ValueError('value is not a valid IPv4 address') from err
        return str(addr)


class IPv4NetworkField(StringField):
    '''
    IPv4 network field. This field accepts CIDR notation networks in the form of ``A.B.C.D/Z``.
    '''
    storage_type = str

    def __init__(self, min_prefix_len: int = None, max_prefix_len: int = None, **kwargs):
        '''
        :param min_prefix_len: minimum subnet prefix length (/X), in bits
        :param max_prefix_len: maximum subnet prefix length (/X), in bits
        '''
        super().__init__(**kwargs)
        self.min_prefix_len = min_prefix_len
        self.max_prefix_len = max_prefix_len

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        value = super()._validate(cfg, value)

        try:
            net = IPv4Network(value)
        except ValueError as err:
            raise ValueError('value is not a valid IPv4 Network (CIDR)') from err

        if self.min_prefix_len and net.prefixlen < self.min_prefix_len:
            raise ValueError('value must be at least a /%d subnet' % self.min_prefix_len)

        if self.max_prefix_len and net.prefixlen > self.max_prefix_len:
            raise ValueError('value must be smaller than a /%d subnet' % self.max_prefix_len)

        return str(net)


class HostnameField(StringField):
    '''
    A field representing a network hostname or, optionally, a network address.
    '''
    storage_type = str
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
        :param value: value to validate
        '''
        value = super()._validate(cfg, value)

        try:
            addr = IPv4Address(value)
        except:
            pass
        else:
            if self.allow_ipv4:
                return str(addr)
            raise ValueError('value is not a valid DNS hostname')

        # value is a hostname
        if self.resolve:
            # resolve hostname to IPv4 address
            try:
                name = socket.gethostbyname(value)
            except OSError as err:
                raise ValueError('DNS resolution failed') from err
            else:
                return name

        # Validate that the value *looks* like a DNS hostname or Windows NetBios name
        dns_match = self.HOSTNAME_REGEX.match(value)
        nb_match = self.NETBIOS_REGEX.match(value)
        if not dns_match and not nb_match:
            raise ValueError('value is not a valid hostname')

        return value
