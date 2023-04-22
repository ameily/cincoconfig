#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
from typing import List
from unittest.mock import patch, call, MagicMock
import pytest
from cincoconfig.fields import ListField, ListProxy, IntField
from cincoconfig.core import Schema, Config, ValidationError


class MockConfig:
    def __init__(self):
        self._data = {}
        self._set_default_value = MagicMock()


class TestListProxy:
    def test_create(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        assert wrap == [1, 2, 3]

    def test_eq_list(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        assert wrap == [1, 2, 3]

    def test_eq_proxy(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        wrap2 = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        assert wrap == wrap2

    def test_eq_not_list(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        assert wrap != "hello"

    def test_append(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        wrap.append("4")
        assert wrap == [1, 2, 3, 4]

    def test_add_list(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        wrap2 = wrap + [4, 5]
        assert wrap2 == [1, 2, 3, 4, 5]

    def test_add_wrapper(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        wrap2 = ListProxy(MockConfig(), ListField(IntField()), [4, "5"])
        wrap3 = wrap + wrap2
        assert wrap3 == [1, 2, 3, 4, 5]

    def test_iadd(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        wrap += [4, 5]
        assert wrap == [1, 2, 3, 4, 5]

    def test_setitem(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        wrap[1] = "5"
        assert wrap == [1, 5, 3]

    def test_setitem_slice(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        wrap[1:3] = ["4", "5"]
        assert wrap == [1, 4, 5]

    def test_copy(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        wrap2 = wrap.copy()
        assert wrap == wrap2
        assert wrap.list_field is wrap2.list_field
        assert wrap.cfg is wrap2.cfg

    def test_insert(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        wrap.insert(1, "6")
        assert wrap == [1, 6, 2, 3]

    def test_to_basic_schema(self):
        schema = Schema()
        schema.x = IntField(default=1)
        schema.y = IntField(default=2)
        field = ListField(schema)
        assert field.to_basic(MockConfig(), [schema()]) == [{"x": 1, "y": 2}]

    def test_validate_schema_dict(self):
        schema = Schema()
        schema.x = IntField(default=1)
        schema.y = IntField(default=2)
        cfg = MockConfig()
        proxy = ListProxy(cfg, ListField(schema))

        check = proxy._validate({"x": 10})
        assert isinstance(check, Config)
        assert check.x == 10
        assert check.y == 2
        assert check._parent is cfg
        assert check._schema is schema

    def test_validate_schema_config(self):
        schema = Schema()
        schema.x = IntField(default=1)
        schema.y = IntField(default=2)
        cfg = MockConfig()
        proxy = ListProxy(cfg, ListField(schema))

        val = schema()
        val.x = 10
        check = proxy._validate(val)
        assert isinstance(check, Config)
        assert check is val
        assert check._parent is cfg
        assert check._schema is schema

    def test_validate_schema_invalid(self):
        schema = Schema()
        schema.x = IntField(default=1)
        schema.y = IntField(default=2)
        cfg = MockConfig()
        proxy = ListProxy(cfg, schema)

        with pytest.raises(ValueError):
            proxy._validate(100)

    def test_extend_list(self):
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        with patch.object(wrap, "_validate") as mock_validate:
            mock_validate.side_effect = [4, 5]
            wrap.extend([4, "5"])
            mock_validate.mock_calls = [call(4), call("5")]

        assert wrap == [1, 2, 3, 4, 5]

    def test_extend_proxy(self):
        cfg = MockConfig()
        field = IntField()
        wrap = ListProxy(cfg, ListField(field), [1, 2, "3"])
        with patch.object(wrap, "_validate") as mock_validate:
            wrap.extend(ListProxy(cfg, ListField(field), [4, 5]))
            mock_validate.assert_not_called()

        assert wrap == [1, 2, 3, 4, 5]

    def test_validate_item_valid(self):
        schema = Schema()
        field = IntField()
        list_field = schema.x = ListField(field)
        config = schema()
        proxy = ListProxy(config, list_field)
        with patch.object(field, "validate") as mock_validate:
            retval = mock_validate.return_value = object()
            assert proxy._validate(2) is retval
            mock_validate.assert_called_once_with(config, 2)

    def test_validate_item_error(self):
        schema = Schema()
        field = IntField()
        list_field = schema.x = ListField(field)
        config = schema()
        proxy = ListProxy(config, list_field)
        orig_exc = ValueError("asdf")
        with patch.object(field, "validate") as mock_validate:
            mock_validate.side_effect = orig_exc
            with pytest.raises(ValueError):
                proxy._validate(2)

    def test_validate_item_error_friendly_name(self):
        schema = Schema()
        field = IntField()
        list_field = schema.x = ListField(field)
        config = schema()
        proxy = ListProxy(config, list_field)
        orig_exc = ValueError("asdf")
        with patch.object(field, "validate") as mock_validate:
            mock_validate.side_effect = orig_exc
            with pytest.raises(ValueError):
                proxy._validate(2)

    def test_validate_item_validation_error(self):
        schema = Schema()
        field = IntField()
        list_field = schema.x = ListField(field)
        config = schema()
        proxy = ListProxy(config, list_field)
        orig_exc = ValidationError(config, list_field, ValueError("asdf"))
        with patch.object(field, "validate") as mock_validate:
            mock_validate.side_effect = orig_exc
            with pytest.raises(ValueError):
                proxy._validate(2)

    def test_listfield_no_field(self):
        schema = Schema()
        list_field = schema.lst = ListField()
        config = schema()

        with pytest.raises(TypeError):
            ListProxy(config, list_field)

    def test_get_item_position_exists(self):
        schema = Schema()
        schema.lst = ListField(IntField())
        config = schema()
        proxy = ListProxy(config, schema.lst)
        proxy.extend([1, 2, 3])
        assert proxy._get_item_position(2) == "1"

    def test_get_item_position_not_exists(self):
        schema = Schema()
        schema.lst = ListField(IntField())
        config = schema()
        proxy = ListProxy(config, schema.lst)
        proxy.extend([1, 2, 3])
        assert proxy._get_item_position(10) == "3"

    def test_validate_not_field(self):
        schema = Schema()
        schema.lst = ListField(int)
        config = schema()
        proxy = ListProxy(config, schema.lst)
        with pytest.raises(TypeError):
            proxy._validate(10)


class TestListField:
    def test_storage_type_str(self):
        field = ListField(IntField())
        assert field.storage_type == List[int]

    def test_storage_type_custom(self):
        field = ListField(type)
        assert field.storage_type == List[type]

    def test_storage_type_schema(self):
        schema = Schema()
        field = ListField(schema)
        assert field.storage_type == List[Schema]

    def test_required_not_empty(self):
        field = ListField(IntField(), required=True)
        value = field._validate(MockConfig(), [1, 2, "3"])
        assert value == [1, 2, 3]
        assert value.list_field is field
        assert value.item_field is field.field

    def test_required_empty(self):
        field = ListField(IntField(), required=True)
        with pytest.raises(ValueError):
            field._validate(MockConfig(), [])

    def test_non_list(self):
        field = ListField(IntField())
        with pytest.raises(ValueError):
            field._validate(MockConfig(), "asdf")

    def test_any_validate(self):
        field = ListField()
        value = field.validate(MockConfig(), [1, 2, 3])
        assert value == [1, 2, 3]
        assert isinstance(value, list)

    def test_to_basic(self):
        field = ListField(IntField(), required=True)
        wrap = ListProxy(MockConfig(), ListField(IntField()), [1, 2, "3"])
        assert field.to_basic(MockConfig(), wrap) == [1, 2, 3]

    def test_to_python(self):
        field = ListField(IntField(), required=True)
        wrap = field.to_python(MockConfig(), [1, 2, "3"])
        assert wrap.list_field is field
        assert wrap.item_field is field.field
        assert wrap == [1, 2, 3]

    def test_to_basic_any(self):
        field = ListField()
        value = field.to_basic(MockConfig(), [1, 2, 3])
        assert value == [1, 2, 3]
        assert isinstance(value, list)

    def test_to_python_any(self):
        field = ListField()
        value = field.to_python(MockConfig(), [1, 2, 3])
        assert value == [1, 2, 3]
        assert isinstance(value, list)

    def test_validate_list_proxy(self):
        field = ListField(IntField())
        orig = ListProxy(MockConfig(), field, [1, 2, 3])
        check = field._validate(MockConfig(), ListProxy(MockConfig(), field, orig))
        assert isinstance(check, ListProxy)
        assert check == orig
        assert check is not orig

    def test_default_list_wrap(self):
        cfg = MockConfig()
        field = ListField(IntField(), default=lambda: [1, 2, 3], key="asdf")
        field.__setdefault__(cfg)
        cfg._set_default_value.assert_called_once_with(
            "asdf", ListProxy(cfg, field, [1, 2, 3])
        )

    def test_default_list_copy(self):
        cfg = MockConfig()
        field = ListField(default=[1, 2, 3], key="asdf")
        field.__setdefault__(cfg)
        cfg._set_default_value.assert_called_once_with("asdf", [1, 2, 3])

    def test_to_basic_none(self):
        field = ListField(IntField(), default=None, key="asdf")
        assert field.to_basic(MockConfig(), None) is None

    def test_to_basic_empty(self):
        field = ListField(IntField(), default=None, key="asdf")
        assert field.to_basic(MockConfig(), []) == []
