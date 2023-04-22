#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from unittest.mock import MagicMock
import pytest
from cincoconfig.fields import VirtualField


class MockConfig:
    def __init__(self):
        self._data = {}


class TestVirtualField:
    def getter(self, cfg):
        return "hello"

    def test__getval(self):
        getter = MagicMock()
        getter.return_value = "hello"
        cfg = MockConfig()
        field = VirtualField(getter)
        assert field.__getval__(cfg) == "hello"
        getter.assert_called_once_with(cfg)

    def test__setval_no_setter(self):
        getter = MagicMock()
        getter.return_value = "hello"

        field = VirtualField(getter)
        with pytest.raises(TypeError):
            field.__setval__(MockConfig(), "goodbye")
        getter.assert_not_called()

    def test__setval_setter(self):
        cfg = MockConfig()
        getter = MagicMock()
        getter.return_value = "hello"

        setter = MagicMock()
        field = VirtualField(getter, setter)
        field.__setval__(cfg, "hello")
        setter.assert_called_once_with(cfg, "hello")

    def test_default_error(self):
        with pytest.raises(TypeError):
            field = VirtualField(self.getter, default=1)

    def test_no_setdefault(self):
        getter = MagicMock()
        getter.return_value = "hello"
        cfg = MockConfig()
        field = VirtualField(getter)
        field.__setdefault__(cfg)
        assert cfg._data == {}
