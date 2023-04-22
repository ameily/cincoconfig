#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from cincoconfig.core import Field, ValidationError, Config
from cincoconfig.fields import DictField, DictProxy
from cincoconfig.fields.dict_field import _iterate_dict_like

INVALID = "<INVALID>"


class MockConfig:
    def __init__(self):
        self._data = {}
        self._set_default_value = MagicMock()


class MyField(Field):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate = MagicMock(side_effect=self.__validate)
        self.to_basic = MagicMock(side_effect=lambda cfg, value: value)

    def __validate(self, cfg: Config, value: Any) -> Any:
        if value == INVALID:
            raise ValidationError(cfg, self)
        return value


class TestDictField:
    def test__validate_dict(self):
        field = DictField()
        assert field._validate(MockConfig(), {"x": 1}) == {"x": 1}

    def test__validate_non_dict(self):
        field = DictField()
        with pytest.raises(ValueError):
            field._validate(MockConfig(), "asdf")

    def test_required_empty(self):
        field = DictField(required=True)
        with pytest.raises(ValueError):
            field._validate(MockConfig(), {})

    def test_init_proxy(self):
        field = DictField(MyField(), MyField())
        assert field._use_proxy

    def test__validate_proxy(self):
        field = DictField(MyField(), MyField())
        cfg = MockConfig()
        proxy = field._validate(cfg, {"x": 1})
        assert isinstance(proxy, DictProxy)
        assert proxy == DictProxy(cfg, field, {"x": 1})

    def test_setdefault_proxy(self):
        field = DictField(MyField(), default={"x": 1}, key="foo")
        cfg = MockConfig()
        field.__setdefault__(cfg)
        cfg._set_default_value.assert_called_once_with(
            "foo", DictProxy(cfg, field, {"x": 1})
        )

    def test_setdefault_dict(self):
        field = DictField(default={"x": 1}, key="foo")
        cfg = MockConfig()
        field.__setdefault__(cfg)
        cfg._set_default_value.assert_called_once_with("foo", {"x": 1})

    def test_setdefault_callable(self):
        field = DictField(default=lambda: {"x": 1}, key="foo")
        cfg = MockConfig()
        field.__setdefault__(cfg)
        cfg._set_default_value.assert_called_once_with("foo", {"x": 1})

    def test_to_basic_none(self):
        field = DictField()
        assert field.to_basic(MockConfig(), None) is None

    def test_to_basic_empty(self):
        field = DictField()
        assert field.to_basic(MockConfig(), {}) == {}

    def test_to_basic_dict(self):
        field = DictField()
        basic = field.to_basic(MockConfig(), {"x": 1})
        assert not isinstance(basic, DictProxy)
        assert basic == {"x": 1}

    def test_to_basic_proxy(self):
        value_field = MyField()
        field = DictField(value_field=value_field)
        cfg = MockConfig()
        basic = field.to_basic(cfg, DictProxy(cfg, field, {"x": 1}))
        assert not isinstance(basic, DictProxy)
        assert basic == {"x": 1}
        value_field.to_basic.assert_called_once_with(cfg, 1)

    def test_to_python_proxy(self):
        field = DictField(MyField())
        cfg = MockConfig()
        proxy = field.to_python(cfg, {"x": 1})
        assert isinstance(proxy, DictProxy)
        assert proxy == DictProxy(cfg, field, {"x": 1})

    def test_to_python_dict(self):
        field = DictField()
        value = {"x": 1}
        assert field.to_python(MockConfig(), value) is value


class TestDictProxy:
    def test_iterate_dict_like_dict(self):
        value = {"x": 1}
        assert _iterate_dict_like(value) == list(value.items())

    def test_iterate_dict_like_key_value_pairs(self):
        value = [("x", 1)]
        assert _iterate_dict_like(value) == list(value)

    def test_init_proxy(self):
        field = DictField(MyField())
        cfg = MockConfig()
        proxy = DictProxy(cfg, field, {"x": 1})
        proxy2 = DictProxy(cfg, field, proxy)
        assert proxy == proxy2

    @patch("cincoconfig.fields.dict_field._iterate_dict_like")
    def test_init_iterable(self, mock_iter):
        mock_iter.return_value = [("x", 1)]
        cfg = MockConfig()
        field = DictField(MyField())
        assert DictProxy(cfg, field, {"x": 1}) == {"x": 1}
        mock_iter.assert_called_once_with({"x": 1})

    def test_init_empty(self):
        cfg = MockConfig()
        field = DictField(MyField())
        assert DictProxy(cfg, field) == {}

    def test_init_type_error(self):
        with pytest.raises(TypeError):
            DictProxy(MockConfig(), DictField())

    def test_init_validation_error(self):
        with pytest.raises(ValidationError):
            DictProxy(MockConfig(), DictField(MyField), {INVALID: 1})

    def test_update_proxy(self):
        field = DictField(MyField())
        cfg = MockConfig()
        proxy = DictProxy(cfg, field, {"x": 1, "y": 3})
        proxy2 = DictProxy(cfg, field, {"x": 2, "z": 4})
        proxy.update(proxy2)
        assert proxy == DictProxy(cfg, field, {"x": 2, "y": 3, "z": 4})

    def test_update_iterable(self):
        proxy = DictProxy(MockConfig(), DictField(MyField()), {"y": 2})
        proxy.update({"x": 1})
        assert proxy == {"x": 1, "y": 2}

    def test_update_kwargs(self):
        proxy = DictProxy(MockConfig(), DictField(value_field=MyField()), {"y": 2})
        proxy.update(x=1)
        assert proxy == {"x": 1, "y": 2}

    def test_update_kwargs_validation_error(self):
        proxy = DictProxy(MockConfig(), DictField(value_field=MyField()))
        with pytest.raises(ValidationError):
            proxy.update(x=INVALID)

    def test_update_validation_error(self):
        field = DictField(value_field=MyField())
        cfg = MockConfig()
        proxy = DictProxy(cfg, field, {"x": 1})
        with pytest.raises(ValidationError):
            proxy.update({"y": 2, "z": INVALID})

    def test_copy(self):
        proxy = DictProxy(MockConfig(), DictField(MyField()), {"x": 1})
        proxy2 = proxy.copy()
        assert proxy == proxy2
        assert proxy is not proxy2
        assert isinstance(proxy2, DictProxy)

    def test_setitem(self):
        proxy = DictProxy(MockConfig(), DictField(MyField()), {"x": 1})
        proxy["x"] = 2
        proxy["y"] = 3
        assert proxy == {"x": 2, "y": 3}

    def test_setitem_validation_error(self):
        proxy = DictProxy(MockConfig(), DictField(MyField()))
        with pytest.raises(ValidationError):
            proxy[INVALID] = 1

    def test_validate_ok(self):
        key = MyField()
        value = MyField()
        cfg = MockConfig()
        proxy = DictProxy(cfg, DictField(key, value))
        assert proxy._validate("x", 1) == ("x", 1)
        key._validate.assert_called_once_with(cfg, "x")
        value._validate.assert_called_once_with(cfg, 1)

    def test_validate_invalid_key(self):
        key = MyField()
        value = MyField()
        cfg = MockConfig()
        proxy = DictProxy(cfg, DictField(key, value))
        with pytest.raises(ValidationError):
            proxy._validate(INVALID, 1)

    def test_validate_invalid_value(self):
        key = MyField()
        value = MyField()
        cfg = MockConfig()
        proxy = DictProxy(cfg, DictField(key, value))
        with pytest.raises(ValidationError):
            proxy._validate("x", INVALID)

    def test_setdefault(self):
        proxy = DictProxy(MockConfig(), DictField(MyField()), {"x": 1})
        proxy.setdefault("x", 2)
        proxy.setdefault("y", 3)
        assert proxy == {"x": 1, "y": 3}

    def test_setdefault_validation_error(self):
        proxy = DictProxy(MockConfig(), DictField(MyField()), {"x": 1})
        with pytest.raises(ValidationError):
            proxy.setdefault(INVALID, 1)

    def test_ref_path(self):
        proxy = DictProxy(MockConfig(), DictField(MyField(), key="foo"))
        assert proxy._ref_path("bar") == "foo[bar]"

    def test_eq_none(self):
        proxy = DictProxy(MockConfig(), DictField(MyField()))
        assert (proxy == None) is False

    def test_eq_not_a_dict(self):
        proxy = DictProxy(MockConfig(), DictField(MyField()))
        assert (proxy == 1) is False
