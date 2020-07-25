from unittest.mock import MagicMock

import pytest

from cincoconfig.abc import Field
from cincoconfig.config import Schema, Config
from cincoconfig.fields import InstanceMethodField


class TestSchema:

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

    def test_validate_ignore_methods(self):
        getter = MagicMock()
        schema = Schema()
        schema.x = InstanceMethodField(getter)
        schema.x.__getval__ = MagicMock()
        config = schema()

        schema._validate(config)
        assert not schema.x.__getval__.called

    def test_get_all_fields(self):
        schema = Schema()
        schema.x = Field()
        schema.sub1.y = Field()
        schema.sub1.sub2.z = Field()
        schema.sub1.a = Field()
        schema.sub3.b = Field()

        check = schema.get_all_fields()
        assert check == [
            ('x', schema, schema.x),
            ('sub1', schema, schema.sub1),
            ('sub1.y', schema.sub1, schema.sub1.y),
            ('sub1.sub2', schema.sub1, schema.sub1.sub2),
            ('sub1.sub2.z', schema.sub1.sub2, schema.sub1.sub2.z),
            ('sub1.a', schema.sub1, schema.sub1.a),
            ('sub3', schema, schema.sub3),
            ('sub3.b', schema.sub3, schema.sub3.b)
        ]

    def test_getitem(self):
        schema = Schema()
        schema.x = Field()
        schema.y.z = Field()

        assert schema['x'] is schema.x
        assert schema['y'] is schema.y
        assert schema['y.z'] is schema.y.z

    def test_getitem_keyerror(self):
        schema = Schema()
        with pytest.raises(KeyError):
            x = schema['x']

    def test_getitem_keyerror_not_schema(self):
        schema = Schema()
        schema.x = Field()
        with pytest.raises(KeyError):
            y = schema['x.y']
