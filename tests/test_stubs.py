import pytest
from cincoconfig.fields import StringField, VirtualField
from cincoconfig.core import Schema, Field
from cincoconfig.stubs import (
    get_annotation_typestr,
    get_arg_annotation,
    get_method_annotation,
    get_retval_annotation,
    generate_stub,
)


class TestStubs:
    def test_get_annotation_typestr_field(self):
        field = StringField(key="hello")
        assert get_annotation_typestr(field) == "str"

    def test_get_annotation_typestr_type_module(self):
        custom_type = type("CustomType", tuple(), {})
        custom_type.__module__ = "a.b.c"
        field = Field(key="helo")
        field.storage_type = custom_type

        assert get_annotation_typestr(field) == "a.b.c.CustomType"

    def test_get_annotation_typestr_schema(self):
        schema = Schema()
        assert get_annotation_typestr(schema) == "cincoconfig.core.Schema"

    def test_get_annotation_typestr_str(self):
        field = Field(key="hello")
        field.storage_type = "asdf"
        assert get_annotation_typestr(field) == "asdf"

    def test_get_annotation_type_any(self):
        field = Field(key="hello")
        field.storage_type = ""
        assert get_annotation_typestr(field) == "typing.Any"

    def test_get_arg_annotation(self):
        assert get_arg_annotation("hello", str) == "hello: str"

    def test_get_retval_annotation(self):
        assert get_retval_annotation(str) == " -> str"

    def test_get_retval_annotation_invalid(self):
        assert get_retval_annotation(10) == ""

    def test_get_method_annotation_kwonly(self):
        def meth(obj, x: int, y: str = None, *, z=None, **kwargs) -> int:
            pass

        schema = Schema()
        schema.instance_method("hello")(meth)
        instance_method = schema.hello

        expected = (
            "def hello(self, x: int, y: str, *, z: typing.Any, **kwargs) -> int: ..."
        )
        assert get_method_annotation("hello", instance_method) == expected

    def test_get_method_annotation_kwonly_varargs(self):
        def meth(obj, x: int, y: "asdf" = None, *args, z=None, **kwargs) -> int:
            pass

        schema = Schema()
        schema.instance_method("hello")(meth)
        instance_method = schema.hello

        expected = "def hello(self, x: int, y: asdf, *args, z: typing.Any, **kwargs) -> int: ..."
        assert get_method_annotation("hello", instance_method) == expected

    def test_get_method_annotation_var_kw(self):
        def meth(obj, x: int, *args, **kwargs):
            pass

        schema = Schema()
        schema.instance_method("hello")(meth)
        instance_method = schema.hello

        expected = "def hello(self, x: int, *args, **kwargs): ..."
        assert get_method_annotation("hello", instance_method) == expected

    def test_generate_stub_schema(self):
        schema = Schema()
        schema.x = VirtualField(lambda x: None)
        schema.y = StringField()

        stub = generate_stub(schema, "Thing").split("\n")
        assert "class Thing(cincoconfig.core.ConfigType):" in stub
        assert "    x: typing.Any" in stub
        assert "    y: str" in stub
        assert "    def __init__(self, y: str): ..." in stub

    def test_generate_stub_config(self):
        schema = Schema()
        schema.x = VirtualField(lambda x: None)
        schema.y = StringField()
        config = schema()

        stub = generate_stub(config, "Thing").split("\n")
        assert "class Thing(cincoconfig.core.ConfigType):" in stub
        assert "    x: typing.Any" in stub
        assert "    y: str" in stub
        assert "    def __init__(self, y: str): ..." in stub

    def test_generate_stub_configtype(self):
        schema = Schema()
        schema.x = VirtualField(lambda x: None)
        schema.y = StringField()
        Thing = schema.make_type("Thing")

        stub = generate_stub(Thing).split("\n")
        assert "class Thing(cincoconfig.core.ConfigType):" in stub
        assert "    x: typing.Any" in stub
        assert "    y: str" in stub
        assert "    def __init__(self, y: str): ..." in stub

    def test_generate_stub_no_class_name(self):
        schema = Schema()
        schema.x = VirtualField(lambda x: None)
        schema.y = StringField()

        with pytest.raises(TypeError):
            generate_stub(schema)

    def test_generate_stub_instance_methods(self):
        def meth1(thing, x: int) -> None:
            pass

        def meth2(thing, y: str) -> int:
            pass

        schema = Schema()
        schema.instance_method("hello")(meth1)
        schema.instance_method("goodbye")(meth2)

        stub = generate_stub(schema, "Thing").split("\n")
        assert "    def hello(self, x: int) -> None: ..." in stub
        assert "    def goodbye(self, y: str) -> int: ..." in stub

    def test_generate_stub_invalid_type(self):
        with pytest.raises(TypeError):
            generate_stub(100, "asdf")
