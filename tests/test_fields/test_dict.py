#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import pytest
from cincoconfig.fields import DictField


class MockConfig:

    def __init__(self):
        self._data = {}


class TestDictField:

    def test__validate_dict(self):
        field = DictField()
        assert field._validate(MockConfig(), {'x': 1}) == {'x': 1}

    def test__validate_non_dict(self):
        field = DictField()
        with pytest.raises(ValueError):
            field._validate(MockConfig(), 'asdf')

    def test_required_empty(self):
        field = DictField(required=True)
        with pytest.raises(ValueError):
            field._validate(MockConfig(), {})
