#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import socket
from unittest.mock import patch

import pytest
from cincoconfig.fields import (
    IPv4AddressField,
    IPv4NetworkField,
    HostnameField,
    PortField,
)


class MockConfig:
    def __init__(self):
        self._data = {}


class TestIPv4AddressField:
    def test_valid_ipv4(self):
        field = IPv4AddressField()
        assert field.validate(MockConfig(), "192.168.1.1") == "192.168.1.1"

    def test_invalid_ipv4(self):
        field = IPv4AddressField()
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "300.1.2.a")


class TestIPv4NetworkField:
    def test_valid_net(self):
        field = IPv4NetworkField()
        assert field.validate(MockConfig(), "192.168.1.0/24") == "192.168.1.0/24"

    def test_invalid_net(self):
        field = IPv4NetworkField()
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "300.1.2.a/42")

    def test_min_prefix_good(self):
        field = IPv4NetworkField(min_prefix_len=8)
        assert field._validate(MockConfig(), "192.168.0.0/16") == "192.168.0.0/16"

    def test_min_prefix_bad(self):
        field = IPv4NetworkField(min_prefix_len=16)
        with pytest.raises(ValueError):
            field._validate(MockConfig(), "10.0.0.0/8")

    def test_max_prefix_good(self):
        field = IPv4NetworkField(max_prefix_len=16)
        assert field._validate(MockConfig(), "10.0.0.0/8") == "10.0.0.0/8"

    def test_max_prefix_bad(self):
        field = IPv4NetworkField(max_prefix_len=31)
        with pytest.raises(ValueError):
            field._validate(MockConfig(), "10.10.10.1/32")


class TestHostnameField:
    def test_valid_ipv4(self):
        field = HostnameField(allow_ipv4=True)
        assert field.validate(MockConfig(), "192.168.1.1") == "192.168.1.1"

    def test_no_ipv4(self):
        field = HostnameField(allow_ipv4=False)
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "192.168.1.1")

    @patch("socket.gethostbyname")
    def test_valid_hostname_resolve(self, gethostbyname):
        gethostbyname.return_value = "TEST"
        field = HostnameField(resolve=True)
        assert field.validate(MockConfig(), "localhost") == "TEST"
        gethostbyname.assert_called_once_with("localhost")

    def test_valid_dnsname(self):
        field = HostnameField()
        assert field.validate(MockConfig(), "google.com") == "google.com"

    def test_valid_netbios(self):
        field = HostnameField()
        assert field.validate(MockConfig(), "some_host") == "some_host"

    def test_invalid_dnsname(self):
        field = HostnameField()
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "<.google.com")

    @patch("socket.gethostbyname")
    def test_resolve_failed(self, gethostbyname):
        gethostbyname.side_effect = OSError()
        field = HostnameField(resolve=True)
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "some_host")

        gethostbyname.assert_called_once_with("some_host")


class TestPortField:
    def test_port_valid(self):
        field = PortField()
        assert field.validate(MockConfig(), 8080) == 8080
        assert field.min == 1
        assert field.max == 2**16 - 1
