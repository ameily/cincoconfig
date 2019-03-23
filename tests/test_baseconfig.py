from unittest.mock import MagicMock
import pytest
from cincoconfig.abc import BaseConfig, BaseSchema, Field


class TestBaseConfig:

    def test_add_field_dynamic(self):
        schema = BaseSchema(dynamic=True)
        config = BaseConfig(schema)
        assert config._add_field('hello', 'world') == 'world'
        assert config._fields['hello'] == 'world'

    def test_add_field_failed(self):
        schema = BaseSchema()
        config = BaseConfig(schema)

        with pytest.raises(TypeError):
            config._add_field('hello', 'world')

    def test_get_field_base(self):
        schema = BaseSchema()
        schema._fields['hello'] = 'world'
        config = BaseConfig(schema)

        assert config._get_field('hello') == 'world'

    def test_get_field_dynamic(self):
        schema = BaseSchema()
        config = BaseConfig(schema)
        config._fields['hello'] = 'world'
        assert config._get_field('hello') == 'world'
