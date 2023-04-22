from unittest.mock import MagicMock, patch, call

import pytest

from cincoconfig.core import Schema, Config, Field, ConfigType, ValidationError
from cincoconfig.fields import InstanceMethodField, FeatureFlagField


class TestSchema:
    def test_setkey(self):
        schema = Schema()
        schema.__setkey__(Schema(), "hello")
        assert schema._key == "hello"

    def test_add_field_field(self):
        field = Field()
        field.__setkey__ = MagicMock()
        schema = Schema()
        schema._add_field("hello", field)
        field.__setkey__.assert_called_once_with(schema, "hello")

    def test_add_field_schema(self):
        schema = Schema()
        child = Schema()
        child.__setkey__ = MagicMock()
        schema._add_field("hello", child)
        child.__setkey__.assert_called_once_with(schema, "hello")

    @patch("cincoconfig.core.ConfigTypeField")
    def test_add_field_config_type(self, mock_ct_field_cls):
        mock_ct_field = mock_ct_field_cls.return_value = MagicMock()
        mock_ct_field.__setkey__ = MagicMock()
        schema = Schema()
        schema._add_field("x", ConfigType)
        assert schema._fields == {"x": mock_ct_field}
        mock_ct_field.__setkey__.assert_called_once_with(schema, "x")

    def test_add_field_other(self):
        schema = Schema()
        with pytest.raises(TypeError):
            schema._add_field("hello", "world")

    def test_get_field_exists(self):
        schema = Schema()
        schema._fields["hello"] = "x"
        assert schema._get_field("hello") == "x"

    def test_get_field_no_exists(self):
        schema = Schema()
        assert schema._get_field("hello") is None

    def test_env_true(self):
        schema = Schema(env=True)
        assert schema._env_prefix == "" and isinstance(schema._env_prefix, str)

    def test_setkey_inherit_env(self):
        schema = Schema(env=True)
        child = Schema()
        child.__setkey__(schema, "child")
        assert child._env_prefix == "CHILD"

    def test_setkey_inherit_env_append(self):
        schema = Schema(env="ASDF")
        child = Schema()
        child.__setkey__(schema, "child")
        assert child._env_prefix == "ASDF_CHILD"

    def test_setkey_env_false(self):
        schema = Schema(env="ASDF")
        child = Schema(env=False)
        child.__setkey__(schema, "child")
        assert child._env_prefix is False

    def test_setattr_field(self):
        field = Field()
        field.__setkey__ = MagicMock()
        schema = Schema()
        schema.field = field

        assert field.__setkey__.called_once_with(schema, "field")
        assert schema._fields["field"] is field

    def test_getattr(self):
        schema = Schema()
        field = Field()
        schema.field = field

        assert schema.field is field

    def test_getattr_new(self):
        schema = Schema()
        field = schema.field
        assert isinstance(field, Schema)
        assert field._key == "field"

    def test_iter(self):
        schema = Schema()
        subfield = Field()
        topfield = Field()
        schema.sub.field = subfield
        schema.field = topfield
        items = sorted(list(schema.__iter__()), key=lambda x: x[0])
        assert items == [("field", topfield), ("sub", schema.sub)]

    def test_call(self):
        schema = Schema()
        cfg = schema()
        assert isinstance(cfg, Config)
        assert cfg._schema is schema

    @patch("cincoconfig.support.make_type")
    def test_make_type(self, mock_make_type):
        schema = Schema()
        retval = mock_make_type.return_value
        assert schema.make_type("asdf", module="qwer", key_filename="zxcv") is retval
        mock_make_type.assert_called_once_with(schema, "asdf", "qwer", "zxcv")

    @patch("cincoconfig.fields.instance_method")
    def test_instance_method_decorator(self, mock_method):
        schema = Schema()
        assert schema.instance_method("asdf") is mock_method.return_value
        mock_method.assert_called_once_with(schema, "asdf")

    def test_validate_ignore_methods(self):
        getter = MagicMock()
        schema = Schema()
        schema.x = InstanceMethodField(getter)
        schema.x.__getval__ = MagicMock()
        config = schema()

        schema._validate(config)
        assert not schema.x.__getval__.called

    @patch("cincoconfig.support.get_all_fields")
    def test_get_all_fields(self, mock_get_all_fields):
        schema = Schema()
        schema.get_all_fields()
        mock_get_all_fields.assert_called_once_with(schema)

    def test_getitem(self):
        schema = Schema()
        schema.x = Field()
        schema.y.z = Field()

        assert schema["x"] is schema.x
        assert schema["y"] is schema.y
        assert schema["y.z"] is schema.y.z

    def test_getitem_missing_schema(self):
        schema = Schema()
        assert isinstance(schema["x"], Schema)

    def test_getitem_keyerror_not_schema(self):
        schema = Schema()
        schema.x = Field()
        with pytest.raises(TypeError):
            y = schema["x.y"]

    def test_setitem(self):
        schema = Schema()
        field = schema["x.y"] = Field()
        assert isinstance(schema._fields["x"], Schema)
        assert schema._fields["x"]._fields["y"] is field

    def test_setitem_typeerror(self):
        schema = Schema()
        schema.x = Field()
        with pytest.raises(TypeError):
            schema["x.y"] = Field()

    def test_getattr_add_field(self):
        schema = Schema()
        mock_add_field = MagicMock(return_value=Schema())
        object.__setattr__(schema, "_add_field", mock_add_field)
        schema.x.y = Field()
        mock_add_field.assert_called_once()

    @patch("cincoconfig.support.generate_argparse_parser")
    def test_generate_argparse_parser(self, mock_gen_parser):
        schema = Schema()
        schema.generate_argparse_parser(x=1, y=2)
        mock_gen_parser.assert_called_once_with(schema, x=1, y=2)

    def test_validator(self):
        schema = Schema()
        schema._validators = MagicMock()
        assert schema.validator("asdf") == "asdf"
        schema._validators.append.assert_called_once_with("asdf")

    def test_validate_collect_errors(self):
        schema_error = ValidationError(None, None, None)
        field_error = ValidationError(None, None, None)
        schema = Schema()
        schema._validators.append(MagicMock(side_effect=schema_error))
        schema.x = Field()
        schema.x.validate = MagicMock(side_effect=field_error)

        config = schema()

        errors = schema._validate(config, collect_errors=True)
        assert errors == [field_error, schema_error]

    def test_validate_collect_errors_other(self):
        schema_error = ValueError()
        field_error = ValueError()
        schema = Schema()
        schema._validators.append(MagicMock(side_effect=schema_error))
        schema.x = Field()
        schema.x.validate = MagicMock(side_effect=field_error)

        config = schema()

        errors = schema._validate(config, collect_errors=True)
        assert len(errors) == 2
        assert isinstance(errors[0], ValidationError)
        assert errors[0].exc is field_error
        assert isinstance(errors[1], ValidationError)
        assert errors[1].exc is schema_error

    def test_feature_flag_fields(self):
        schema = Schema()
        schema.x = Field()
        schema.y = FeatureFlagField()
        schema.z = FeatureFlagField()
        assert list(schema._feature_flag_fields) == [schema.y, schema.z]

    def test_is_feature_enabled_true(self):
        schema = Schema()
        schema.x = Field()
        schema.y = FeatureFlagField()
        schema.z = FeatureFlagField()
        config = schema()
        config._data.update({"y": True, "z": True})
        assert schema._is_feature_enabled(config)

    def test_is_feature_disabled_false(self):
        schema = Schema()
        schema.x = Field()
        schema.y = FeatureFlagField()
        schema.z = FeatureFlagField()
        config = schema()
        config._data.update({"y": True, "z": False})
        assert not schema._is_feature_enabled(config)

    def test_validate_feature_flag_disabled(self):
        cfg = MagicMock()
        schema = Schema()
        schema._validators.append(MagicMock(side_effect=ValueError()))

        schema._is_feature_enabled = MagicMock(return_value=False)
        schema._validate(cfg)
        schema._is_feature_enabled.assert_called_once_with(cfg)
