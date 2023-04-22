from unittest.mock import patch, MagicMock, call
import argparse

import pytest

from cincoconfig.fields import (
    StringField,
    IntField,
    BoolField,
    FloatField,
    VirtualField,
)
from cincoconfig.core import Schema, Field, Config
from cincoconfig.support import (
    generate_argparse_parser,
    get_fields,
    is_value_defined,
    make_type,
    get_all_fields,
    cmdline_args_override,
    reset_value,
    validator,
    item_ref_path,
    asdict,
    _list_asdict,
)


class TestSupportFuncs:
    @patch("cincoconfig.support.ArgumentParser")
    def test_generate_argparse_parser(self, mock_argparse):
        parser = MagicMock()
        mock_argparse.return_value = parser
        schema = Schema()
        schema.long_name = StringField(help="asdf")
        schema.sub.short_name = IntField()
        schema.enable = BoolField()
        schema.runtime = FloatField()
        schema.ignore_me2 = Field()  # no storage_type

        retval = generate_argparse_parser(schema, x=1, y=2)
        assert retval is parser
        mock_argparse.assert_called_once_with(x=1, y=2)
        parser.add_argument.call_args_list == [
            call(
                "--long-name",
                action="store",
                dest="long_name",
                help="asdf",
                metavar="LONG_NAME",
            ),
            call(
                "--sub-short-name",
                action="store",
                dest="sub.short_name",
                help=None,
                metavar="SUB_SHORT_NAME",
            ),
            call("--enable", action="store_true", help=None, dest="enable"),
            call("--no-enable", action="store_false", help=None, dest="enable"),
            call("--runtime", action="store", dest="runtime", help=None),
        ]

    def test_get_all_fields_schema(self):
        schema = Schema()
        schema.x = Field()
        schema.sub1.y = Field()
        schema.sub1.sub2.z = Field()
        schema.sub1.a = Field()
        schema.sub3.b = Field()

        check = get_all_fields(schema)
        assert check == [
            ("x", schema, schema.x),
            ("sub1", schema, schema.sub1),
            ("sub1.y", schema.sub1, schema.sub1.y),
            ("sub1.sub2", schema.sub1, schema.sub1.sub2),
            ("sub1.sub2.z", schema.sub1.sub2, schema.sub1.sub2.z),
            ("sub1.a", schema.sub1, schema.sub1.a),
            ("sub3", schema, schema.sub3),
            ("sub3.b", schema.sub3, schema.sub3.b),
        ]

    def test_get_all_fields_config(self):
        schema = Schema()
        schema.x = Field()
        schema.sub1.y = Field()
        schema.sub1.sub2.z = Field()
        schema.sub1.a = Field()
        schema.sub3.b = Field()
        config = schema()

        check = get_all_fields(config)
        assert check == [
            ("x", schema, schema.x),
            ("sub1", schema, schema.sub1),
            ("sub1.y", schema.sub1, schema.sub1.y),
            ("sub1.sub2", schema.sub1, schema.sub1.sub2),
            ("sub1.sub2.z", schema.sub1.sub2, schema.sub1.sub2.z),
            ("sub1.a", schema.sub1, schema.sub1.a),
            ("sub3", schema, schema.sub3),
            ("sub3.b", schema.sub3, schema.sub3.b),
        ]

    def test_make_type(self):
        schema = Schema()
        schema.x = Field(default=2)
        schema.y = Field()

        CustomConfig = make_type(schema, "CustomConfig")
        cfg = CustomConfig(y=10)
        assert isinstance(cfg, Config)
        assert cfg.x == 2
        assert cfg.y == 10

    def test_cmdline_args_override(self):
        parser = argparse.ArgumentParser()
        schema = Schema()
        schema.w = Field(default="w")
        schema.x = Field(default="x")
        schema.y.z = Field(default="z")
        config = schema()

        parser.add_argument("-x", action="store")
        parser.add_argument("-z", action="store", dest="y.z")
        parser.add_argument("-i", action="store")
        parser.add_argument("-j", action="store")
        args = parser.parse_args(["-x", "1", "-z", "2", "-j", "3"])

        cmdline_args_override(config, args, ignore=["j"])

        assert config.x == "1"
        assert config.y.z == "2"
        assert config.w == "w"

    def test_cmdline_args_ocverride_single_ignore(self):
        parser = argparse.ArgumentParser()
        schema = Schema()
        schema.w = Field(default="w")
        schema.x = Field(default="x")
        schema.y.z = Field(default="z")
        config = schema()

        parser.add_argument("-x", action="store")
        parser.add_argument("-z", action="store", dest="y.z")
        parser.add_argument("-i", action="store")
        parser.add_argument("-j", action="store")
        args = parser.parse_args(["-x", "1", "-z", "2", "-j", "3"])

        cmdline_args_override(config, args, ignore="j")

        assert config.x == "1"
        assert config.y.z == "2"
        assert config.w == "w"

    def test_validator_schema(self):
        schema = Schema()
        schema._validators = MagicMock()
        func = lambda cfg: cfg
        assert validator(schema)(func) is func
        schema._validators.append.assert_called_once_with(func)

    def test_validator_field(self):
        field = Field()
        func = lambda cfg, value: cfg
        assert validator(field)(func) is func
        assert field.validator is func

    def test_item_ref_path(self):
        item = MagicMock()
        retval = item._ref_path = object()
        assert item_ref_path(item) is retval

    def test_get_fields_schema(self):
        schema = Schema()
        schema.x = Field()
        schema.sub1.y = Field()
        assert get_fields(schema) == [("x", schema.x), ("sub1", schema.sub1)]

    def test_get_fields_config(self):
        schema = Schema(dynamic=True)
        schema.x = Field()
        schema.sub1.y = Field()
        config = schema()
        config.z = 2
        assert get_fields(config) == [
            ("z", config._fields["z"]),
            ("x", schema.x),
            ("sub1", schema.sub1),
        ]

    def test_get_fields_type(self):
        schema = Schema()
        schema.x = Field()
        schema.y = IntField()
        schema.sub1.y = Field()
        assert get_fields(schema, IntField) == [("y", schema.y)]

    def test_asdict(self):
        schema = Schema(dynamic=True)
        schema.x = Field()
        schema.sub1.y = Field()
        schema.a = VirtualField(lambda cfg: 100)
        config = schema()
        config.x = 1
        config.sub1.y = 2
        config.z = 3
        assert asdict(config) == {"x": 1, "z": 3, "sub1": {"y": 2}}

    def test_asdict_virtual(self):
        schema = Schema()
        schema.x = Field()
        schema.sub1.y = Field()
        schema.a = VirtualField(lambda cfg: 100)
        config = schema()
        config.x = 1
        config.sub1.y = 2
        assert asdict(config, virtual=True) == {"x": 1, "sub1": {"y": 2}, "a": 100}

    def test_asdict_copy(self):
        schema = Schema()
        config = schema()
        test = config._data["x"] = {"a": 1}
        result = asdict(config)
        assert result["x"] == test
        assert result["x"] is not test

    @patch("cincoconfig.support._list_asdict")
    def test_asdict_list(self, mock_list_asdict):
        mock_list_asdict.return_value = object()
        schema = Schema()
        config = schema()
        lst = config._data["x"] = [1, 2, 3]
        virtual = object()
        assert asdict(config, virtual=virtual) == {"x": mock_list_asdict.return_value}
        mock_list_asdict.assert_called_once_with([1, 2, 3], virtual=virtual)

    @patch("cincoconfig.support._list_asdict")
    def test_list_asdict_nested_list(self, mock_list_asdict):
        mock_list_asdict.return_value = object()
        virtual = object()
        assert _list_asdict([[1], 2, 3], virtual=virtual) == [
            mock_list_asdict.return_value,
            2,
            3,
        ]
        mock_list_asdict.assert_called_once_with([1], virtual=virtual)

    @patch("cincoconfig.support.asdict")
    def test_list_asdict_nested_config(self, mock_asdict):
        schema = Schema()
        config = schema()
        mock_asdict.return_value = object()
        virtual = object()
        assert _list_asdict([config], virtual=virtual) == [mock_asdict.return_value]
        mock_asdict.assert_called_once_with(config, virtual=virtual)

    def test_list_asdict_copy(self):
        x = {"a": 1}
        y = [x]
        result = _list_asdict(y, False)
        assert result == y
        assert result is not y
        assert result[0] == x
        assert result[0] is not x

    def test_is_value_defined(self):
        config = MagicMock(_default_value_keys=set(["x"]))
        assert is_value_defined(config, "x") is False
        assert is_value_defined(config, "y") is True

    def test_is_value_defined_nested(self):
        config = {"sub": MagicMock(_default_value_keys=set(["x"]))}
        assert is_value_defined(config, "sub.x") is False
        assert is_value_defined(config, "sub.y") is True

    def test_reset_value(self):
        config = MagicMock()
        field = config._get_field.return_value = MagicMock(__setdefault__=MagicMock())
        reset_value(config, "x")
        config._get_field.assert_called_once_with("x")
        field.__setdefault__.assert_called_once_with(config)

    def test_reset_value_nested(self):
        config = MagicMock()
        field = config._get_field.return_value = MagicMock(__setdefault__=MagicMock())
        reset_value({"sub": config}, "sub.x")
        config._get_field.assert_called_once_with("x")
        field.__setdefault__.assert_called_once_with(config)

    def test_reset_value_attribute_error(self):
        config = MagicMock()
        config._get_field.return_value = None
        with pytest.raises(AttributeError):
            reset_value(config, "x")
