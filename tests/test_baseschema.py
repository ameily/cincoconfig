from unittest.mock import MagicMock
from cincoconfig.abc import BaseSchema, Field


class TestBaseSchema:

    def test_setkey(self):
        schema = BaseSchema()
        schema.__setkey__(None, 'hello')
        assert schema._key == 'hello'

    def test_add_field_field(self):
        field = Field()
        field.__setkey__ = MagicMock()
        schema = BaseSchema()
        schema._add_field('hello', field)
        field.__setkey__.assert_called_once_with(schema, 'hello')

    def test_add_field_schema(self):
        schema = BaseSchema()
        child = BaseSchema()
        child.__setkey__ = MagicMock()
        schema._add_field('hello', child)
        child.__setkey__.assert_called_once_with(schema, 'hello')

    def test_add_field_other(self):
        schema = BaseSchema()
        assert schema._add_field('hello', 'world') == 'world'

    def test_get_field_exists(self):
        schema = BaseSchema()
        schema._fields['hello'] = 'x'
        assert schema._get_field('hello') == 'x'

    def test_get_field_no_exists(self):
        schema = BaseSchema()
        assert schema._get_field('hello') is None
