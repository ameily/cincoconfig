#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import pytest
from cincoconfig.fields import NumberField, IntField, FloatField


class MockConfig:
    def __init__(self):
        self._data = {}


class TestIntField:
    def test_valid_int(self):
        field = IntField()
        assert field.validate(MockConfig(), "100") == 100

    def test_invalid_int(self):
        field = IntField()
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "asdf")

    def test_min_valid(self):
        field = IntField(min=5)
        assert field.validate(MockConfig(), "5") == 5

    def test_min_invalid(self):
        field = IntField(min=5)
        with pytest.raises(ValueError):
            field.validate(MockConfig(), 4)

    def test_max_valid(self):
        field = IntField(max=10)
        assert field.validate(MockConfig(), 10) == 10

    def test_max_invalid(self):
        field = IntField(max=10)
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "11")

    def test_non_int_convertable(self):
        field = IntField()
        with pytest.raises(ValueError):
            field.validate(MockConfig(), [])


class TestFloatField:
    def test_valid_float(self):
        field = FloatField()
        assert field.validate(MockConfig(), "100.5") == 100.5

    def test_invalid_float(self):
        field = FloatField()
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "asdf")
