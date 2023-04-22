from unittest.mock import patch, MagicMock, PropertyMock
import pytest
from cincoconfig.core import ConfigFormat
from cincoconfig.formats.json import JsonConfigFormat
from cincoconfig.formats.bson import BsonConfigFormat
from cincoconfig.formats.yaml import YamlConfigFormat
from cincoconfig.formats.xml import XmlConfigFormat
from cincoconfig.formats.pickle import PickleConfigFormat


class TestFormatRegistry:
    def setup_method(self, _):
        ConfigFormat._ConfigFormat__registry = {}
        ConfigFormat._ConfigFormat__initialized = False

    def test_register(self):
        fmt = MagicMock
        ConfigFormat.register("blah", fmt)
        assert ConfigFormat._ConfigFormat__registry["blah"] is fmt

    def test_get(self):
        fmt = MagicMock()
        fmt.return_value = "hello"
        ConfigFormat._ConfigFormat__registry["blah"] = fmt

        ConfigFormat._ConfigFormat__initialized = True
        check = ConfigFormat.get("blah", x=1, y="2")
        fmt.assert_called_once_with(x=1, y="2")
        assert check == "hello"

    @patch.object(ConfigFormat, "initialize_registry")
    def test_get_initialize(self, mock_init):
        ConfigFormat._ConfigFormat__registry["blah"] = MagicMock()
        ConfigFormat.get("blah")
        mock_init.assert_called_once()

    def test_get_no_exists(self):
        with pytest.raises(KeyError):
            ConfigFormat.get("asdfasdfasdf")

    def test_base_formats(self):
        ConfigFormat.initialize_registry()

        assert ConfigFormat._ConfigFormat__registry == {
            "json": JsonConfigFormat,
            "yaml": YamlConfigFormat,
            "bson": BsonConfigFormat,
            "pickle": PickleConfigFormat,
            "xml": XmlConfigFormat,
        }

    def test_initialize_cache(self):
        ConfigFormat.initialize_registry()
        reg = ConfigFormat._ConfigFormat__registry = object()
        ConfigFormat.initialize_registry()
        assert ConfigFormat._ConfigFormat__registry is reg
