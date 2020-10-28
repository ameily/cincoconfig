import argparse
from unittest.mock import MagicMock, patch, mock_open
import pytest
from cincoconfig.formats.registry import FormatRegistry
from cincoconfig.config import Config, Schema, Field, AnyField
from cincoconfig.fields import IncludeField
from cincoconfig.version import __version__


class MockFormatter:

    def __init__(self):
        self.dumps = MagicMock()
        self.loads = MagicMock()

        self.dumps.return_value = b'hello, world'
        self.loads.return_value = {'x': 1}


class MockFormatInclude:

    def __init__(self):
        self.loads = MagicMock(return_value={'include': 'blah.txt', 'include2': None})


class TestConfig:

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

        assert isinstance(config._data['sub'], Config)
        assert config._data['sub']._schema is sub
        assert config._data['sub']._parent is config

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
        assert isinstance(config._fields['x'], AnyField)

    def test_setattr_non_dynamic(self):
        schema = Schema()
        config = schema()
        with pytest.raises(TypeError):
            config.x = 2

    def test_setattr_config_dict(self):
        schema = Schema()
        schema.blah.x = Field()
        config = schema()

        config.blah = {'x': 2}
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

        with pytest.raises(TypeError):
            config.blah = 2

    def test_getitem(self):
        schema = Schema()
        schema.x = Field(default=2)
        config = schema()
        assert config['x'] == 2

    def test_to_tree(self):
        schema = Schema(dynamic=True)
        schema.x = Field(default=2)
        schema.blah.y = Field(default=3)

        config = schema()
        config.z = 4
        assert config.to_tree() == {'x': 2, 'blah': {'y': 3}, 'z': 4}

    def test_iter(self):
        schema = Schema(dynamic=True)
        schema.x = Field(default=2)
        schema.blah.y = Field(default=3)

        config = schema()
        config.z = 4

        items = sorted(list(config.__iter__()), key=lambda x: x[0])
        assert items == [('blah', config.blah), ('x', 2), ('z', 4)]

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
        config['x'] = 2
        assert config._data['x'] == 2

    @patch('cincoconfig.formats.registry.FormatRegistry.get')
    def test_dumps(self, fr_get):
        fmt = MockFormatter()
        fr_get.return_value = fmt
        schema = Schema()
        schema.x = Field(default=2)
        config = schema()
        msg = config.dumps(format='blah')

        assert msg == b'hello, world'
        fmt.dumps.assert_called_once_with(config, {'x': 2})
        fr_get.assert_called_once_with('blah')

    @patch('cincoconfig.formats.registry.FormatRegistry.get')
    def test_loads(self, fr_get):
        fmt = MockFormatter()
        load_tree = MagicMock()
        fr_get.return_value = fmt
        config = Config(Schema())
        object.__setattr__(config, 'load_tree', load_tree)

        config.loads('hello', format='blah')
        config.load_tree.assert_called_once_with({'x': 1})
        fmt.loads.assert_called_once_with(config, b'hello')
        fr_get.assert_called_once_with('blah')

    @patch('cincoconfig.config.open', new_callable=mock_open, read_data=b'hello')
    @patch('cincoconfig.config.Config.loads')
    def test_load(self, loads, mop):
        loads.return_value = {'x': 1}
        config = Config(Schema())
        object.__setattr__(config, 'loads', loads)

        assert config.load('blah.txt', format='blah') == {'x': 1}
        loads.assert_called_once_with(b'hello', 'blah')
        mop.assert_called_once_with('blah.txt', 'rb')

    @patch('cincoconfig.config.open', new_callable=mock_open)
    @patch('cincoconfig.config.Config.dumps')
    def test_save(self, dumps, mop):
        dumps.return_value = b'hello'
        config = Config(Schema())
        config.save('blah.txt', format='blah')

        dumps.assert_called_once_with('blah')
        mop.assert_called_once_with('blah.txt', 'wb')
        mop().write.assert_called_once_with(b'hello')

    def test_version(self):
        assert isinstance(__version__, str)

    def test_getitem_nested(self):
        schema = Schema()
        schema.x.y = AnyField(default=2)
        config = schema()

        assert config['x.y'] == 2

    def test_setitem_nested(self):
        schema = Schema()
        schema.x.y = AnyField(default=2)
        config = schema()

        config['x.y'] = 10
        assert config['x.y'] == 10

    def test_include_field(self):
        fmt = MagicMock()
        mock_factory = MagicMock()
        mock_factory.return_value = fmt

        schema = Schema()
        field = IncludeField()
        field.include = MagicMock(return_value={'x': 1, 'y': 2})
        schema.include = field
        schema.include2 = IncludeField()
        schema.include3 = IncludeField()
        config = schema()

        result = config._process_includes(schema, {'include': 'blah.txt', 'include2': None}, mock_factory)
        field.include.assert_called_once_with(config, fmt, 'blah.txt', {'include': 'blah.txt', 'include2': None})
        assert result == {'x': 1, 'y': 2}

    def test_nested_include(self):
        mock_factory = MagicMock()
        schema = Schema()
        schema.top.field = Field()
        config = schema()

        sub = {'asdf': 1}
        process_includes = config._process_includes
        mock_pi = MagicMock()
        mock_pi.return_value = {'hello': 1}
        object.__setattr__(config, '_process_includes', mock_pi)
        result = process_includes(schema, {'top': sub}, mock_factory)
        mock_pi.assert_called_once_with(schema.top, sub, mock_factory)

        assert result == {'top': {'hello': 1}}

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
        object.__setattr__(schema.x, '_validate', mock)
        config.validate()

        mock.assert_called_once_with(config.x)

    def test_load_tree_validate(self):
        schema = Schema()
        schema.x = Field()
        config = schema()

        mock_validate = MagicMock()
        object.__setattr__(config, 'validate', mock_validate)
        config.load_tree({'x': 1})
        mock_validate.assert_called_once_with()

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

    def test_cmdline_args_override(self):
        parser = argparse.ArgumentParser()
        schema = Schema()
        schema.w = Field(default='w')
        schema.x = Field(default='x')
        schema.y.z = Field(default='z')
        config = schema()

        parser.add_argument('-x', action='store')
        parser.add_argument('-z', action='store', dest='y.z')
        parser.add_argument('-i', action='store')
        parser.add_argument('-j', action='store')
        args = parser.parse_args(['-x', '1', '-z', '2', '-j', '3'])

        config.cmdline_args_override(args, ignore=['j'])

        assert config.x == '1'
        assert config.y.z == '2'
        assert config.w == 'w'

    def test_cmdline_args_ocverride_single_ignore(self):
        parser = argparse.ArgumentParser()
        schema = Schema()
        schema.w = Field(default='w')
        schema.x = Field(default='x')
        schema.y.z = Field(default='z')
        config = schema()

        parser.add_argument('-x', action='store')
        parser.add_argument('-z', action='store', dest='y.z')
        parser.add_argument('-i', action='store')
        parser.add_argument('-j', action='store')
        args = parser.parse_args(['-x', '1', '-z', '2', '-j', '3'])

        config.cmdline_args_override(args, ignore='j')

        assert config.x == '1'
        assert config.y.z == '2'
        assert config.w == 'w'

    def test_in_flat(self):
        schema = Schema()
        schema.x = Field()
        config = schema()
        config.x = 2

        assert 'x' in config

    def test_in_nested(self):
        schema = Schema()
        schema.x.y = Field()
        config = schema()
        config.x.y = 2

        assert 'x.y' in config

    def test_not_in(self):
        schema = Schema()
        schema.x = Field()
        config = schema()
        config.x = 2

        assert 'z' not in config

    def test_in_not_config(self):
        schema = Schema()
        schema.x = Field()
        config = schema()
        config.x = 2

        assert 'x.y' not in config
