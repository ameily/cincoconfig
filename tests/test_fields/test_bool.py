#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import pytest
from cincoconfig.fields import BoolField, FeatureFlagField


class MockConfig:
    def __init__(self):
        self._data = {}


class TestBoolField:
    @pytest.mark.parametrize("value", BoolField.TRUE_VALUES)
    def test_valid_true_str(self, value):
        field = BoolField()
        assert field.validate(MockConfig(), value) is True

    @pytest.mark.parametrize("value", BoolField.FALSE_VALUES)
    def test_valid_false_str(self, value):
        field = BoolField()
        assert field.validate(MockConfig(), value) is False

    def test_true_int(self):
        field = BoolField()
        assert field.validate(MockConfig(), 1) is True

    def test_false_int(self):
        field = BoolField()
        assert field.validate(MockConfig(), 0) is False

    def test_true_float(self):
        field = BoolField()
        assert field.validate(MockConfig(), 1.0) is True

    def test_false_float(self):
        field = BoolField()
        assert field.validate(MockConfig(), 0.0) is False

    def test_bool(self):
        field = BoolField()
        assert field.validate(MockConfig(), True) is True

    def test_not_convertable(self):
        field = BoolField()
        with pytest.raises(ValueError):
            field.validate(MockConfig(), b"true")

    def test_invalid_str(self):
        field = BoolField()
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "asdf")


class TestFeatureFlagFIeld:
    def test_enabled(self):
        field = FeatureFlagField(key="flag")
        cfg = MockConfig()
        cfg._data["flag"] = True

        assert field.is_feature_enabled(cfg)

    def test_disabled(self):
        field = FeatureFlagField(key="flag")
        cfg = MockConfig()
        cfg._data["flag"] = False

        assert not field.is_feature_enabled(cfg)
