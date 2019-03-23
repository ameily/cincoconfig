from unittest.mock import patch, MagicMock, PropertyMock
import pytest
from cincoconfig.formats.registry import FormatRegistry, _FormatRegistrySingleton
from cincoconfig.formats.json import JsonConfigFormat
from cincoconfig.formats.bson import BsonConfigFormat
from cincoconfig.formats.yaml import YamlConfigFormat
from cincoconfig.formats.pickle import PickleConfigFormat


class TestFormatRegistry:

    def test_register(self):
        fmt = MagicMock
        FormatRegistry.register('blah', fmt)
        assert FormatRegistry._formats['blah'] is fmt

    def test_get(self):
        reg = _FormatRegistrySingleton()
        fmt = MagicMock()
        fmt.return_value = 'hello'
        reg._formats['blah'] = fmt

        check = reg.get('blah', x=1, y='2')
        fmt.assert_called_once_with(x=1, y='2')
        assert check == 'hello'

    def test_get_no_exists(self):
        with pytest.raises(KeyError):
            fmt = FormatRegistry.get('asdfasdfasdf')

    def test_get_calls_init(self):
        reg = _FormatRegistrySingleton()
        reg._initialize = MagicMock()
        reg._formats['blah'] = lambda: 'hello'
        assert reg.get('blah') == 'hello'
        reg._initialize.assert_called_once_with()

    def test_register_calls_init(self):
        reg = _FormatRegistrySingleton()
        reg._initialize = MagicMock()
        reg.register('blah', 'hello')
        reg._initialize.assert_called_once_with()
        assert reg._formats['blah'] == 'hello'

    def test_base_formats(self):
        reg = _FormatRegistrySingleton()
        reg._initialize()

        assert reg._formats == {
            'json': JsonConfigFormat,
            'yaml': YamlConfigFormat,
            'bson': BsonConfigFormat,
            'pickle': PickleConfigFormat
        }
