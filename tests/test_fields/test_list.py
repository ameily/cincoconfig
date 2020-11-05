#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
from typing import List
from unittest.mock import patch, call
import pytest
from cincoconfig.fields import ListField, ListProxy, IntField
from cincoconfig.config import Schema, Config


class MockConfig:

    def __init__(self):
        self._data = {}


class TestListProxy:

    def test_create(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        assert wrap == [1, 2, 3]

    def test_eq_list(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        assert wrap == [1, 2, 3]

    def test_eq_proxy(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        wrap2 = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        assert wrap == wrap2

    def test_eq_not_list(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        assert wrap != 'hello'

    def test_append(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        wrap.append('4')
        assert wrap == [1, 2, 3, 4]

    def test_add_list(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        wrap2 = wrap + [4, 5]
        assert wrap2 == [1, 2, 3, 4, 5]

    def test_add_wrapper(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        wrap2 = ListProxy(MockConfig(), IntField(), [4, '5'])
        wrap3 = wrap + wrap2
        assert wrap3 == [1, 2, 3, 4, 5]

    def test_iadd(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        wrap += [4, 5]
        assert wrap == [1, 2, 3, 4, 5]

    def test_setitem(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        wrap[1] = '5'
        assert wrap == [1, 5, 3]

    def test_copy(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        wrap2 = wrap.copy()
        assert wrap == wrap2
        assert wrap.field is wrap2.field
        assert wrap.cfg is wrap2.cfg

    def test_insert(self):
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        wrap.insert(1, '6')
        assert wrap == [1, 6, 2, 3]

    def test_to_basic_schema(self):
        schema = Schema()
        schema.x = IntField(default=1)
        schema.y = IntField(default=2)
        field = ListField(schema)
        assert field.to_basic(MockConfig(), [schema()]) == [{'x': 1, 'y': 2}]

    def test_validate_schema_dict(self):
        schema = Schema()
        schema.x = IntField(default=1)
        schema.y = IntField(default=2)
        cfg = MockConfig()
        proxy = ListProxy(cfg, schema)

        check = proxy._validate({'x': 10})
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
        proxy = ListProxy(cfg, schema)

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
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        with patch.object(wrap, '_validate') as mock_validate:
            mock_validate.side_effect = [4, 5]
            wrap.extend([4, '5'])
            mock_validate.mock_calls = [call(4), call('5')]

        assert wrap == [1, 2, 3, 4, 5]

    def test_extend_proxy(self):
        cfg = MockConfig()
        field = IntField()
        wrap = ListProxy(cfg, field, [1, 2, '3'])
        with patch.object(wrap, '_validate') as mock_validate:
            wrap.extend(ListProxy(cfg, field, [4, 5]))
            mock_validate.assert_not_called()

        assert wrap == [1, 2, 3, 4, 5]


class TestListField:

    def test_storage_type_str(self):
        field = ListField(IntField())
        assert field.storage_type == List[int]

    def test_storage_type_custom(self):
        field = ListField(type)
        assert field.storage_type is List

    def test_storage_type_schema(self):
        schema = Schema()
        field = ListField(schema)
        assert field.storage_type == List[Schema]

    def test_required_not_empty(self):
        field = ListField(IntField(), required=True)
        value = field._validate(MockConfig(), [1, 2, '3'])
        assert value == [1, 2, 3]
        assert value.field is field.field

    def test_required_empty(self):
        field = ListField(IntField(), required=True)
        with pytest.raises(ValueError):
            field._validate(MockConfig(), [])

    def test_non_list(self):
        field = ListField(IntField())
        with pytest.raises(ValueError):
            field._validate(MockConfig(), 'asdf')

    def test_any_validate(self):
        field = ListField()
        value = field.validate(MockConfig(), [1, 2, 3])
        assert value == [1, 2, 3]
        assert isinstance(value, list)

    def test_to_basic(self):
        field = ListField(IntField(), required=True)
        wrap = ListProxy(MockConfig(), IntField(), [1, 2, '3'])
        assert field.to_basic(MockConfig(), wrap) == [1, 2, 3]

    def test_to_python(self):
        field = ListField(IntField(), required=True)
        wrap = field.to_python(MockConfig(), [1, 2, '3'])
        assert wrap.field is field.field
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
        orig = ListProxy(MockConfig(), IntField(), [1, 2, 3])
        check = field._validate(MockConfig(), ListProxy(MockConfig(), IntField(), orig))
        assert isinstance(check, ListProxy)
        assert check == orig
        assert check is not orig

    def test_default_list_wrap(self):
        cfg = MockConfig()
        field = ListField(IntField(), default=lambda: [1, 2, 3], key='asdf')
        field.__setdefault__(cfg)
        assert isinstance(cfg._data['asdf'], ListProxy)
        assert cfg._data['asdf'] == ListProxy(cfg, field.field, [1, 2, 3])

    def test_to_basic_none(self):
        field = ListField(IntField(), default=None, key='asdf')
        assert field.to_basic(MockConfig(), None) is None

    def test_to_basic_empty(self):
        field = ListField(IntField(), default=None, key='asdf')
        assert field.to_basic(MockConfig(), []) == []
