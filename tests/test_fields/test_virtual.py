#
# Copyright (C) 2019 Adam Meily
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
        return 'hello'

    def test__getval(self):
        getter = MagicMock()
        getter.return_value = 'hello'
        cfg = MockConfig()
        field = VirtualField(getter)
        assert field.__getval__(cfg) == 'hello'
        getter.assert_called_once_with(cfg)

    def test__setval(self):
        getter = MagicMock()
        getter.return_value = 'hello'

        field = VirtualField(getter)
        with pytest.raises(TypeError):
            field.__setval__(MockConfig(), 'goodbye')
        getter.assert_not_called()

    def test_no_setdefault(self):
        getter = MagicMock()
        getter.return_value = 'hello'
        cfg = MockConfig()
        field = VirtualField(getter)
        field.__setdefault__(cfg)
        assert cfg._data == {}



