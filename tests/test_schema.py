from unittest.mock import MagicMock
from cincoconfig.abc import Field
from cincoconfig.config import Schema, Config
from cincoconfig.fields import InstanceMethodField


class TestConfig:

    def test_setattr_field(self):
        field = Field()
        field.__setkey__ = MagicMock()
        schema = Schema()
        schema.field = field

        assert field.__setkey__.called_once_with(schema, 'field')
        assert schema._fields['field'] is field

    def test_getattr(self):
        schema = Schema()
        field = Field()
        schema.field = field

        assert schema.field is field

    def test_getattr_new(self):
        schema = Schema()
        field = schema.field
        assert isinstance(field, Schema)
        assert field._key == 'field'

    def test_iter(self):
        schema = Schema()
        subfield = Field()
        topfield = Field()
        schema.sub.field = subfield
        schema.field = topfield
        items = sorted(list(schema.__iter__()), key=lambda x: x[0])
        assert items == [('field', topfield), ('sub', schema.sub)]

    def test_call(self):
        schema = Schema()
        cfg = schema()
        assert isinstance(cfg, Config)
        assert cfg._schema is schema

    def test_make_type(self):
        schema = Schema()
        schema.x = Field(default=2)
        schema.y = Field()

        CustomConfig = schema.make_type('CustomConfig')
        a = CustomConfig(y=10)
        assert isinstance(a, Config)
        assert a.x == 2
        assert a.y == 10

    def test_instance_method_decorator(self):
        schema = Schema()
        @schema.instance_method('test')
        def meth(cfg):
            pass

        assert isinstance(schema._fields['test'], InstanceMethodField)
        assert schema._fields['test'].method is meth
