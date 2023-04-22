#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
import os
from unittest.mock import patch, MagicMock, PropertyMock
import pytest

from cincoconfig.core import Field, Schema, Config, ValidationError


class MockConfig:
    def __init__(self, data=None, parent=None, key=None):
        self._data = data or {}
        self._parent = parent
        self._key = key
        self._schema = Schema()
        self._set_default_value = MagicMock()

    def _full_path(self):
        return ""


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
        field = Field(name="name", key="key")
        assert field.name == "name"

    def test_setval(self):
        field = Field(key="key")
        field.__setval__(self.cfg, "hello")
        assert self.cfg._data == {"key": "hello"}

    def test_getval(self):
        field = Field(key="key")
        self.cfg._data["key"] = "hello"
        assert field.__getval__(self.cfg) == "hello"

    def test_setkey(self):
        field = Field()
        field.__setkey__(self.cfg._schema, "key")
        assert field._key == "key"

    def test_setdefault(self):
        field = Field(key="key", default="hello")
        field.__setdefault__(self.cfg)
        self.cfg._set_default_value.assert_called_once_with("key", "hello")

    def test_to_python(self):
        field = Field()
        x = "hello"
        assert field.to_python(self.cfg, x) is x

    def test_to_basic(self):
        field = Field()
        x = "hello"
        assert field.to_basic(self.cfg, x) is x

    def test__validate(self):
        field = Field()
        x = "hello"
        assert field._validate(self.cfg, x) is x

    def test_required(self):
        field = Field(required=True, key="key")
        with pytest.raises(ValueError):
            field.validate(self.cfg, None)

    def test_not_required(self):
        field = Field(key="key")
        assert field.validate(self.cfg, None) is None

    def test_validate_value(self):
        field = Field(key="key")
        x = "hello"
        assert field.validate(self.cfg, x) is x

    def test_validate_validator_valid(self):
        field = Field(key="key", validator=lambda cfg, value: "HELLO")
        assert field.validate(self.cfg, "asdf") == "HELLO"

    def test_validate_validator_invalid(self):
        def inner(cfg, value):
            raise KeyError()

        field = Field(key="key", validator=inner)
        with pytest.raises(KeyError):
            field.validate(self.cfg, "hello")

    def test_ref_path_flat(self):
        field = Field(key="asdf")
        assert field._ref_path == "asdf"

    def test_ref_path_nested(self):
        root = MagicMock()
        root._key = "asdf"
        root._schema = None
        field = Field(key="value", schema=root)
        assert field._ref_path == "asdf.value"

    def test_full_path(self):
        field = Field(key="x")
        with patch.object(
            Field, "_ref_path", new_callable=PropertyMock
        ) as mock_ref_path:
            retval = mock_ref_path.return_value = object()
            assert field.full_path is retval
            mock_ref_path.assert_called_once()

    def test_short_help_none(self):
        field = Field()
        assert field.help is None
        assert field.short_help is None

    def test_short_help_everything(self):
        field = Field(help="blah")
        assert field.short_help == "blah"

    def test_short_help_paragraph(self):
        field = Field(help="\n\nfirst\nsecond\nthird.\n\nmore\n\n")
        assert field.short_help == "first\nsecond\nthird."
        assert field.help == "first\nsecond\nthird.\n\nmore"

    def test_env_true(self):
        schema = Schema()
        field = Field(env=True)
        field.__setkey__(schema, "field")
        assert field.env == "FIELD"

    def test_setkey_inherit_env(self):
        schema = Schema(env=True)
        field = Field()
        field.__setkey__(schema, "field")
        assert field.env == "FIELD"

    def test_setkey_inherit_env_append(self):
        schema = Schema(env="APP")
        field = Field()
        field.__setkey__(schema, "field")
        assert field.env == "APP_FIELD"

    def test_setkey_env_false(self):
        schema = Schema(env=True)
        field = Field(env=False)
        field.__setkey__(schema, "field")
        assert field.env is False

    @patch.object(os.environ, "get")
    def test_setdefault_env_exists(self, mock_environ_get):
        retval = mock_environ_get.return_value = object()
        cfg = Config(schema=Schema())
        field = Field(env="ASDF", key="field")
        field.__setdefault__(cfg)
        assert cfg._data == {"field": retval}
        mock_environ_get.assert_called_once_with("ASDF")

    @patch.object(os.environ, "get")
    def test_setdefault_env_exists_valid(self, mock_environ_get):
        env = mock_environ_get.return_value = object()
        retval = object()
        cfg = Config(schema=Schema())
        field = Field(env="ASDF", key="field")
        field.validate = MagicMock(return_value=retval)
        field.__setdefault__(cfg)
        field.validate.assert_called_once_with(cfg, env)
        assert cfg._data == {"field": retval}

    @patch.object(os.environ, "get")
    def test_setdefault_env_exists_invalid(self, mock_environ_get):
        env = mock_environ_get.return_value = object()
        retval = object()
        cfg = Config(schema=Schema())
        field = Field(env="ASDF", key="field")
        field.validate = MagicMock(side_effect=ValueError())
        field._default = retval
        with pytest.raises(ValidationError):
            field.__setdefault__(cfg)

        field.validate.assert_called_once_with(cfg, env)

    @patch.object(os.environ, "get")
    def test_setdefault_env_exists_invalid_validationerror(self, mock_environ_get):
        env = mock_environ_get.return_value = object()
        retval = object()
        cfg = Config(schema=Schema())
        field = Field(env="ASDF", key="field")
        err = ValidationError(cfg, field, ValueError("asdf"))
        field.validate = MagicMock(side_effect=err)
        field._default = retval
        with pytest.raises(ValidationError) as exc:
            field.__setdefault__(cfg)

        assert exc.value is err

    @patch.object(os.environ, "get")
    def test_setdefault_env_not_exists(self, mock_environ_get):
        mock_environ_get.return_value = None
        retval = object()
        cfg = Config(schema=Schema())
        field = Field(env="ASDF", key="field")
        field._default = retval
        field.__setdefault__(cfg)
        assert cfg._data == {"field": retval}
        mock_environ_get.assert_called_once_with("ASDF")
