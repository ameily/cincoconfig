#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
from unittest.mock import patch, MagicMock
import pytest

from cincoconfig.abc import Field


class MockConfig:

    def __init__(self, data=None, parent=None, key=None):
        self._data = data or {}
        self._parent = parent
        self._key = key

    def _full_path(self):
        return ''


class TestBaseField:

    def setup_method(self, method=None):
        self.cfg = MockConfig()

    def test_default_value(self):
        field = Field(default=2)
        assert field.default == 2

    def test_default_callable(self):
        field = Field(default=list)
        assert field.default == []

    def test_name(self):
        field = Field(name='name', key='key')
        assert field.name == 'name'

    def test_key_name(self):
        field = Field(key='key')
        assert field.name == 'key'

    def test_setval(self):
        field = Field(key='key')
        field.__setval__(self.cfg, 'hello')
        assert self.cfg._data == {'key': 'hello'}

    def test_getval(self):
        field = Field(key='key')
        self.cfg._data['key'] = 'hello'
        assert field.__getval__(self.cfg) == 'hello'

    def test_setkey(self):
        field = Field()
        field.__setkey__(self.cfg, 'key')
        assert field.key == 'key'

    def test_setdefault(self):
        field = Field(key='key', default='hello')
        field.__setdefault__(self.cfg)
        assert self.cfg._data['key'] == 'hello'

    def test_to_python(self):
        field = Field()
        x = 'hello'
        assert field.to_python(self.cfg, x) is x

    def test_to_basic(self):
        field = Field()
        x = 'hello'
        assert field.to_basic(self.cfg, x) is x

    def test__validate(self):
        field = Field()
        x = 'hello'
        assert field._validate(self.cfg, x) is x

    def test_required(self):
        field = Field(required=True, key='key')
        with pytest.raises(ValueError):
            field.validate(self.cfg, None)

    def test_not_required(self):
        field = Field(key='key')
        assert field.validate(self.cfg, None) is None

    def test_validate_value(self):
        field = Field(key='key')
        x = 'hello'
        assert field.validate(self.cfg, x) is x

    def test_validate_validator_valid(self):
        field = Field(key='key', validator=lambda cfg, value: 'HELLO')
        assert field.validate(self.cfg, 'asdf') == 'HELLO'

    def test_validate_validator_invalid(self):
        def inner(cfg, value):
            raise KeyError()

        field = Field(key='key', validator=inner)
        with pytest.raises(KeyError):
            field.validate(self.cfg, 'hello')

    def test_friendly_name_with_name(self):
        field = Field(name='ASDF', key='asdf')
        cfg = MockConfig()
        assert field.friendly_name(cfg) == 'ASDF'

    def test_friendly_name_same(self):
        field = Field(name='asdf', key='asdf')
        cfg = MockConfig()
        retval = object()
        with patch.object(field, 'full_path') as mock_path:
            mock_path.return_value = retval
            assert field.friendly_name(cfg) is retval
            mock_path.assert_called_once_with(cfg)

    def test_friendly_name_no_name(self):
        field = Field(key='asdf')
        cfg = MockConfig()
        retval = object()
        with patch.object(field, 'full_path') as mock_path:
            mock_path.return_value = retval
            assert field.friendly_name(cfg) is retval
            mock_path.assert_called_once_with(cfg)

    def test_full_path_flat(self):
        field = Field(key='asdf')
        cfg = MockConfig()
        assert field.full_path(cfg) == 'asdf'

    def test_full_path_nested(self):
        # root = MockConfig()
        # level1 = MockConfig(key='level1', parent=root)
        # level2 = MockConfig(key='level2', parent=level1)
        # field = Field(key='value')
        # assert field.full_path(level2) == 'level1.level2.value'
        root = MockConfig()
        root._full_path = MagicMock()
        root._full_path.return_value = 'asdf'
        field = Field(key='value')
        assert field.full_path(root) == 'asdf.value'
        root._full_path.assert_called_once()

