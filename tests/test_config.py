import argparse
import os
from tests.test_fields.test_bool import MockConfig
from unittest.mock import MagicMock, patch, mock_open, PropertyMock

import pytest

from cincoconfig.core import (
    Config,
    Schema,
    Field,
    AnyField,
    ConfigType,
    ValidationError,
    ConfigFormat,
)
from cincoconfig.fields import (
    IncludeField,
    VirtualField,
    SecureField,
    InstanceMethodField,
)
from cincoconfig.version import __version__


class MockFormatter:
    def __init__(self):
        self.dumps = MagicMock()
        self.loads = MagicMock()

        self.dumps.return_value = b"hello, world"
        self.loads.return_value = {"x": 1}


class MockFormatInclude:
    def __init__(self):
        self.loads = MagicMock(return_value={"include": "blah.txt", "include2": None})


class TestConfig:
    def test_add_field_dynamic(self):
        schema = Schema(dynamic=True)
        config = Config(schema)
        assert config._set_value("hello", "world") == "world"
        assert config._data["hello"] == "world"
        assert isinstance(config._fields["hello"], AnyField)

    def test_add_field_failed(self):
        schema = Schema()
        config = Config(schema)

        with pytest.raises(AttributeError):
            config._set_value("hello", "world")

    def test_get_field_base(self):
        schema = Schema()
        field = schema._fields["hello"] = Field()
        config = Config(schema)

        assert config._get_field("hello") is field

    def test_get_field_dynamic(self):
        schema = Schema()
        config = Config(schema)
        config._fields["hello"] = "world"
        assert config._get_field("hello") == "world"

    def test_key_filename_ctor(self):
        cfg = Config(Schema(), key_filename="asdf.txt")
        assert cfg._key_filename == "asdf.txt"
        assert cfg._Config__keyfile.filename == "asdf.txt"

    def test_key_filename_none_ctor(self):
        cfg = Config(Schema())
        assert cfg._key_filename is Config.DEFAULT_CINCOKEY_FILEPATH

    def test_key_filename_parent(self):
        parent = Config(Schema(), key_filename="asdf.txt")
        child = Config(Schema(), parent)
        assert child._key_filename == "asdf.txt"

    def test_key_filename_setter(self):
        parent = Config(Schema(), key_filename="asdf.txt")
        child = Config(Schema(), parent)
        child._key_filename = "qwer.txt"
        assert child._key_filename == "qwer.txt"
        assert parent._key_filename == "asdf.txt"

    def test_key_filename_set_none(self):
        parent = Config(Schema(), key_filename="asdf.txt")
        child = Config(Schema(), parent, key_filename="qwer.txt")
        child._key_filename = None
        assert child._key_filename == "asdf.txt"
        assert parent._key_filename == "asdf.txt"

    def test_keyfile_set(self):
        parent = Config(Schema(), key_filename="asdf.txt")
        child = Config(Schema(), parent, key_filename="qwer.txt")
        assert child._keyfile is not parent._keyfile

    def test_keyfile_parent(self):
        parent = Config(Schema(), key_filename="asdf.txt")
        child = Config(Schema(), parent)
        assert child._keyfile is parent._keyfile

    @patch("cincoconfig.core.Config.DEFAULT_CINCOKEY_FILEPATH", "/path/to/cincokey")
    def test_keyfile_default(self):
        parent = Config(Schema())
        child = Config(Schema(), parent)
        assert child._keyfile is parent._keyfile
        assert child._keyfile.filename == "/path/to/cincokey"

    def test_ref_path(self):
        parent = Config(Schema(key="root"))
        child = Config(Schema(key="child"), parent=parent)
        assert child._ref_path == "root.child"

    def test_ref_path_container(self):
        parent = Config(Schema(key="root"))
        child = Config(Schema(key="child"), parent=parent)
        child._container = MagicMock()
        child._container._get_item_position = MagicMock()
        child._container._get_item_position.return_value = "1"
        assert child._ref_path == "root.child[1]"
        child._container._get_item_position.assert_called_once_with(child)

    def test_ref_path_container_error(self):
        parent = Config(Schema(key="root"))
        child = Config(Schema(key="child"), parent=parent)
        child._container = MagicMock()
        child._container._get_item_position = MagicMock(side_effect=ValueError())
        assert child._ref_path == "root.child"

    def test_ref_path_no_parent(self):
        cfg = Config(Schema(key="child", schema=Schema(key="root")))
        assert cfg._ref_path == "root.child"

    def test_setdefault(self):
        schema = Schema()
        field = Field()
        field.__setdefault__ = MagicMock()
        schema.x = field

        config = schema()
        field.__setdefault__.assert_called_once_with(config)

    def test_subschema(self):
        schema = Schema()
        sub = schema.sub
        config = schema()

        assert isinstance(config._data["sub"], Config)
        assert config._data["sub"]._schema is sub
        assert config._data["sub"]._parent is config

    def test_setattr_field(self):
        schema = Schema()
        field = Field()
        field.__setval__ = MagicMock()
        schema.x = field
        config = schema()

        config.x = 2
        field.__setval__.assert_called_once_with(config, 2)

    def test_setattr_dynamic(self):
        schema = Schema(dynamic=True)
        config = schema()

        config.x = 2
        assert config.x == 2
        assert isinstance(config._fields["x"], AnyField)

    def test_setattr_non_dynamic(self):
        schema = Schema()
        config = schema()
        with pytest.raises(AttributeError):
            config.x = 2

    def test_setattr_config_dict(self):
        schema = Schema()
        schema.blah.x = Field()
        config = schema()

        config.blah = {"x": 2}
        assert config.blah.x == 2

    def test_setattr_value(self):
        schema = Schema()
        field = Field()
        field.__setval__ = MagicMock()
        schema.x = field
        config = schema()
        config.x = 2

        field.__setval__.assert_called_once_with(config, 2)

    def test_setattr_config_no_dict(self):
        schema = Schema()
        schema.blah.x = Field()
        config = schema()

        with pytest.raises(ValidationError):
            config.blah = 2

    def test_getitem(self):
        schema = Schema()
        schema.x = Field(default=2)
        config = schema()
        assert config["x"] == 2

    def test_to_tree(self):
        schema = Schema(dynamic=True)
        schema.x = Field(default=2)
        schema.blah.y = Field(default=3)

        config = schema()
        config.z = 4
        print(config._fields)
        print(config._data)
        assert config.to_tree() == {"x": 2, "blah": {"y": 3}, "z": 4}

    def test_to_tree_include_virtual(self):
        sentinel = object()
        schema = Schema()
        schema.v = VirtualField(getter=lambda config: sentinel)
        config = schema()
        assert config.to_tree(virtual=True) == {"v": sentinel}

    def test_to_tree_exclude_virtual(self):
        sentinel = object()
        schema = Schema()
        schema.v = VirtualField(getter=lambda config: sentinel)
        config = schema()
        assert config.to_tree(virtual=False) == {}

    def test_to_tree_empty_mask_secure(self):
        schema = Schema()
        schema.v = SecureField(method="xor", default=None)
        config = schema()
        assert config.to_tree(sensitive_mask="*") == {"v": None}

    def test_to_tree_sensitive_mask_single(self):
        schema = Schema()
        schema.v = SecureField(method="xor", default="asdf")
        config = schema()
        assert config.to_tree(sensitive_mask="*") == {"v": "****"}

    def test_to_tree_sensitive_mask_multi(self):
        schema = Schema()
        schema.v = SecureField(method="xor", default="asdf")
        config = schema()
        assert config.to_tree(sensitive_mask="<secret>") == {"v": "<secret>"}

    def test_to_tree_sensitive_mask_empty(self):
        schema = Schema()
        schema.v = SecureField(method="xor", default="asdf")
        config = schema()
        assert config.to_tree(sensitive_mask="") == {"v": ""}

    @patch.object(ConfigFormat, "get")
    def test_dumps_to_tree_args(self, fr_get):
        fmt = MockFormatter()
        fr_get.return_value = fmt
        schema = Schema()
        schema.x = Field(default=2)
        config = schema()

        virtual = object()
        sensitive_mask = object()

        mock_to_tree = MagicMock(returnvalue={})
        object.__setattr__(config, "to_tree", mock_to_tree)
        config.dumps(format="blah", virtual=virtual, sensitive_mask=sensitive_mask)
        mock_to_tree.assert_called_once_with(
            virtual=virtual, sensitive_mask=sensitive_mask
        )

    def test_iter(self):
        schema = Schema(dynamic=True)
        schema.x = Field(default=2)
        schema.blah.y = Field(default=3)

        config = schema()
        config.z = 4

        items = sorted(list(config.__iter__()), key=lambda x: x[0])
        assert items == [("blah", config.blah), ("x", 2), ("z", 4)]

    def test_getattr_error(self):
        schema = Schema()
        config = schema()
        with pytest.raises(AttributeError):
            x = config.x

    def test_getattr_dynamic(self):
        schema = Schema(dynamic=True)
        config = schema()
        assert config.x is None

    def test_setitem(self):
        schema = Schema()
        schema.x = Field()
        config = schema()
        config["x"] = 2
        assert config._data["x"] == 2

    @patch.object(ConfigFormat, "get")
    def test_dumps(self, fr_get):
        fmt = MockFormatter()
        fr_get.return_value = fmt
        schema = Schema()
        schema.x = Field(default=2)
        config = schema()
        msg = config.dumps(format="blah")

        assert msg == b"hello, world"
        fmt.dumps.assert_called_once_with(config, {"x": 2})
        fr_get.assert_called_once_with("blah")

    @patch.object(ConfigFormat, "get")
    def test_loads(self, fr_get):
        fmt = MockFormatter()
        load_tree = MagicMock()
        fr_get.return_value = fmt
        config = Config(Schema())
        object.__setattr__(config, "load_tree", load_tree)

        config.loads("hello", format="blah")
        config.load_tree.assert_called_once_with({"x": 1})
        fmt.loads.assert_called_once_with(config, b"hello")
        fr_get.assert_called_once_with("blah")

    @patch("cincoconfig.core.open", new_callable=mock_open, read_data=b"hello")
    @patch("cincoconfig.core.Config.loads")
    def test_load(self, loads, mop):
        loads.return_value = {"x": 1}
        config = Config(Schema())
        object.__setattr__(config, "loads", loads)

        assert config.load("blah.txt", format="blah") == {"x": 1}
        loads.assert_called_once_with(b"hello", "blah")
        mop.assert_called_once_with("blah.txt", "rb")

    @patch("cincoconfig.core.open", new_callable=mock_open)
    @patch("cincoconfig.core.Config.dumps")
    def test_save(self, dumps, mop):
        dumps.return_value = b"hello"
        config = Config(Schema())
        config.save("blah.txt", format="blah")

        dumps.assert_called_once_with("blah")
        mop.assert_called_once_with("blah.txt", "wb")
        mop().write.assert_called_once_with(b"hello")

    def test_version(self):
        assert isinstance(__version__, str)

    def test_getitem_nested(self):
        schema = Schema()
        schema.x.y = AnyField(default=2)
        config = schema()

        assert config["x.y"] == 2

    def test_setitem_nested(self):
        schema = Schema()
        schema.x.y = AnyField(default=2)
        config = schema()

        config["x.y"] = 10
        assert config["x.y"] == 10

    def test_include_field(self):
        fmt = MagicMock()
        mock_factory = MagicMock()
        mock_factory.return_value = fmt

        schema = Schema()
        field = IncludeField()
        field.include = MagicMock(return_value={"x": 1, "y": 2})
        schema.include = field
        schema.include2 = IncludeField()
        schema.include3 = IncludeField()
        config = schema()

        result = config._process_includes(
            schema, {"include": "blah.txt", "include2": None}, mock_factory
        )
        field.include.assert_called_once_with(
            config, fmt, "blah.txt", {"include": "blah.txt", "include2": None}
        )
        assert result == {"x": 1, "y": 2}

    def test_nested_include(self):
        mock_factory = MagicMock()
        schema = Schema()
        schema.top.field = Field()
        config = schema()

        sub = {"asdf": 1}
        process_includes = config._process_includes
        mock_pi = MagicMock()
        mock_pi.return_value = {"hello": 1}
        object.__setattr__(config, "_process_includes", mock_pi)
        result = process_includes(schema, {"top": sub}, mock_factory)
        mock_pi.assert_called_once_with(schema.top, sub, mock_factory)

        assert result == {"top": {"hello": 1}}

    def test_set_config(self):
        schema = Schema()
        schema.x.y = Field()
        config = schema()

        sub = schema.x()
        sub.y = 10
        config.x = sub
        assert sub._parent is config
        assert config.x is sub

    def test_validate(self):
        schema = Schema()
        schema.x.y = Field()
        config = schema()

        mock = MagicMock()
        print(config._data)
        schema.x._validate = mock
        config.validate()

        mock.assert_called_once_with(config.x, collect_errors=False)

    def test_load_tree_validate(self):
        schema = Schema()
        schema.x = Field()
        config = schema()

        mock_validate = MagicMock()
        object.__setattr__(config, "validate", mock_validate)
        config.load_tree({"x": 1})
        mock_validate.assert_called_once_with()

    @patch("cincoconfig.core.os")
    def test_load_tree_ignore_env(self, mock_os):
        env = mock_os.environ.get.return_value = object()
        schema = Schema()
        schema.x = Field(env="ASDF")
        schema.x.__setdefault__ = MagicMock()
        cfg = schema()
        cfg._data = {"x": "qwer"}
        cfg.load_tree({"x": "asdf"})
        assert cfg._data == {"x": "qwer"}
        mock_os.environ.get.assert_called_once_with("ASDF")

    def test_validator(self):
        validator = MagicMock()
        schema = Schema()
        schema.x = Field()

        @schema.validator
        def validate(cfg):
            validator(cfg)

        config = schema()
        config.validate()
        validator.assert_called_once_with(config)

    @patch("cincoconfig.support.cmdline_args_override")
    def test_cmdline_args_override(self, mock_override):
        args = object()
        schema = Schema()
        config = schema()
        config.cmdline_args_override(args, ignore=["j"])

        mock_override.assert_called_once_with(config, args, ["j"])

    def test_in_flat(self):
        schema = Schema()
        schema.x = Field()
        config = schema()
        config.x = 2

        assert "x" in config

    def test_in_nested(self):
        schema = Schema()
        schema.x.y = Field()
        config = schema()
        config.x.y = 2

        assert "x.y" in config

    def test_not_in(self):
        schema = Schema()
        schema.x = Field()
        config = schema()
        config.x = 2

        assert "z" not in config

    def test_in_not_config(self):
        schema = Schema()
        schema.x = Field()
        config = schema()
        config.x = 2

        assert "x.y" not in config

    def test_wrap_validation_error(self):
        schema = Schema()
        field = schema.x = Field()
        config = schema()
        orig_exc = ValueError("asdf")

        with patch.object(field, "validate") as mock_validate:
            mock_validate.side_effect = orig_exc
            with pytest.raises(ValidationError) as excinfo:
                config.__setattr__("x", 2)

            mock_validate.assert_called_once_with(config, 2)
            assert excinfo.value.config is config
            assert excinfo.value.field is field
            assert excinfo.value.exc is orig_exc

    def test_validation_error_str(self):
        schema = Schema()
        field = schema.x.y.z = Field()
        config = schema()
        orig_exc = ValueError("asdf")

        with patch.object(field, "validate") as mock_validate:
            mock_validate.side_effect = orig_exc
            with pytest.raises(ValidationError) as excinfo:
                config.x.y.__setattr__("z", 2)

            assert str(excinfo.value) == "x.y.z: asdf"

    def test_setattr_validation_error_reraise(self):
        schema = Schema()
        field = schema.x = Field()
        config = schema()
        orig_exc = ValidationError(config, field, ValueError("asdf"))

        with patch.object(field, "validate") as mock_validate:
            mock_validate.side_effect = orig_exc
            with pytest.raises(ValidationError) as excinfo:
                config.__setattr__("x", 2)

            assert excinfo.value is orig_exc

    def test_valdiate_wrap_validation_error(self):
        schema = Schema()
        field = schema.x = Field()
        config = schema()
        config.x = 2
        orig_exc = ValueError("asdf")

        with patch.object(field, "validate") as mock_validate:
            mock_validate.side_effect = orig_exc
            with pytest.raises(ValidationError) as excinfo:
                config.validate()

            mock_validate.assert_called_once_with(config, 2)
            assert excinfo.value.config is config
            assert excinfo.value.field is field
            assert excinfo.value.exc is orig_exc

    def test_validate_reraise_validation_error(self):
        schema = Schema()
        field = schema.x = Field()
        config = schema()
        config.x = 2
        orig_exc = ValidationError(config, field, ValueError("asdf"))

        with patch.object(field, "validate") as mock_validate:
            mock_validate.side_effect = orig_exc
            with pytest.raises(ValidationError) as excinfo:
                config.validate()

            mock_validate.assert_called_once_with(config, 2)
            assert excinfo.value is orig_exc

    @patch("cincoconfig.core.open", new_callable=mock_open)
    @patch("cincoconfig.core.os.path.expanduser")
    def test_save_expanduser(self, expanduser, mop):
        expanduser.return_value = "path/to/blah.txt"
        config = Config(Schema())
        config.save("~/blah.txt", format="json")

        expanduser.assert_called_once_with("~/blah.txt")
        mop.assert_called_once_with("path/to/blah.txt", "wb")

    @patch("cincoconfig.core.open", new_callable=mock_open, read_data=b"{}")
    @patch("cincoconfig.core.os.path.expanduser")
    def test_load_expanduser(self, expanduser, mop):
        expanduser.return_value = "path/to/blah.txt"
        config = Config(Schema())

        config.load("~/blah.txt", format="json")
        expanduser.assert_called_once_with("~/blah.txt")
        mop.assert_called_once_with("path/to/blah.txt", "rb")

    def test_configtype_eq(self):
        class Cfg(ConfigType):
            __schema__ = Schema()
            __key_filename__ = None

        cfg = Cfg()
        cfg._data = {"x": 1, "y": 2}
        cfg2 = Cfg()
        cfg2._data = {"x": 1, "y": 2}

        assert cfg.__eq__(cfg2)

    def test_configtype_eq_none(self):
        class Cfg(ConfigType):
            __schema__ = Schema()
            __key_filename__ = None

        cfg = Cfg()
        assert not cfg.__eq__(None)

    def test_configtype_eq_diff_class(self):
        class Cfg(ConfigType):
            __schema__ = Schema()
            __key_filename__ = None

        class Cfg2(ConfigType):
            __schema__ = Schema()
            __key_filename__ = None

        cfg = Cfg()
        cfg2 = Cfg2()
        assert not cfg.__eq__(cfg2)

    def test_configtype_ne(self):
        class Cfg(ConfigType):
            __schema__ = Schema()
            __key_filename__ = None

        cfg = Cfg()
        cfg._data = {"x": 1, "y": 2}
        cfg2 = Cfg()
        cfg2._data = {"x": 1, "y": 3}
        assert not cfg.__eq__(cfg2)

    def test_set_value_config_validation_error(self):
        err = ValidationError(None, None, None)
        schema = Schema()
        schema.x.y = Field()
        schema.x._validators.append(MagicMock(side_effect=err))
        config = schema()
        with pytest.raises(ValidationError) as exc:
            config._set_value("x", {})

        assert exc.value is err

    def test_set_value_config_exc(self):
        err = ValueError()
        schema = Schema()
        schema.x.y = Field()
        schema.x._validators.append(MagicMock(side_effect=err))
        config = schema()
        with pytest.raises(ValidationError) as exc:
            config._set_value("x", {})

        assert exc.value.exc is err

    def test_full_path(self):
        schema = Schema()
        config = schema()
        with patch.object(
            Config, "_ref_path", new_callable=PropertyMock
        ) as mock_ref_path:
            retval = mock_ref_path.return_value = object()
            assert config.full_path is retval
            mock_ref_path.assert_called_once()

    def test_to_tree_ignore_instance_method(self):
        schema = Schema()
        schema._add_field("x", InstanceMethodField(lambda cfg: 1))
        config = schema()
        config._data["x"] = 1
        assert config.to_tree() == {}

    def test_to_tree_to_basic_exc(self):
        err = ValueError()
        schema = Schema()
        field = schema.x = Field()
        field.to_basic = MagicMock(side_effect=err)
        config = schema()
        config.x = 2
        with pytest.raises(ValidationError) as exc:
            config.to_tree()

        assert exc.value.exc is err
        field.to_basic.assert_called_once_with(config, 2)

    def test_to_tree_to_basic_validation_error(self):
        err = ValidationError(None, None, None)
        schema = Schema()
        field = schema.x = Field()
        field.to_basic = MagicMock(side_effect=err)
        config = schema()
        config.x = 2
        with pytest.raises(ValidationError) as exc:
            config.to_tree()

        assert exc.value is err

    def test_load_tree_to_python_exc(self):
        err = ValueError()
        schema = Schema()
        field = schema.x = Field()
        field.to_python = MagicMock(side_effect=err)
        config = schema()
        with pytest.raises(ValidationError) as exc:
            config.load_tree({"x": 2})

        assert exc.value.exc is err
        field.to_python.assert_called_once_with(config, 2)

    def test_load_tree_to_python_validation_error(self):
        err = ValidationError(None, None, None)
        schema = Schema()
        field = schema.x = Field()
        field.to_python = MagicMock(side_effect=err)
        config = schema()
        with pytest.raises(ValidationError) as exc:
            config.load_tree({"x": 2})

        assert exc.value is err

    def test_validate_collect_errors(self):
        schema = Schema()
        schema._validate = MagicMock()
        config = schema()
        config.validate(collect_errors=True)
        schema._validate.assert_called_once_with(config, collect_errors=True)

    def test_load_tree_no_validate(self):
        schema = Schema()
        schema.x = Field(required=True)
        config = schema()
        assert config.load_tree({}, validate=False) is None

    def test_default_keys(self):
        schema = Schema()
        schema.a.b = Field(default=0)
        schema.x = Field(default=1)
        schema.y = Field(default=2)
        schema.z = Field(default=3)
        config = schema(y=2, z=4)
        assert config._default_value_keys == set(["a", "x"])

    def test_default_keys_override(self):
        schema = Schema()
        schema.x = Field(default=1)
        config = schema()
        config.x = 1
        assert config._default_value_keys == set()

    def test_default_keys_config_override(self):
        schema = Schema()
        schema.x.y = Field(default=1)
        config = schema()
        config.x = {"y": 2}
        assert config._default_value_keys == set()

    def test_set_default_value(self):
        schema = Schema()
        config = schema()
        config._set_default_value("x", "asdf")
        assert config._data == {"x": "asdf"}
        assert config._default_value_keys == set(["x"])
