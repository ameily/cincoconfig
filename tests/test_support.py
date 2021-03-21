
from unittest.mock import patch, MagicMock, call
import argparse

from cincoconfig.fields import StringField, IntField, BoolField, FloatField
from cincoconfig.core import Schema, Field, Config
from cincoconfig.support import (generate_argparse_parser, make_type, get_all_fields,
                                 cmdline_args_override, validator)


class TestSupportFuncs:

    @patch('cincoconfig.support.ArgumentParser')
    def test_generate_argparse_parser(self, mock_argparse):
        parser = MagicMock()
        mock_argparse.return_value = parser
        schema = Schema()
        schema.long_name = StringField(help='asdf')
        schema.sub.short_name = IntField()
        schema.enable = BoolField()
        schema.runtime = FloatField()
        schema.ignore_me2 = Field()  # no storage_type

        retval = generate_argparse_parser(schema, x=1, y=2)
        assert retval is parser
        mock_argparse.assert_called_once_with(x=1, y=2)
        parser.add_argument.call_args_list == [
            call('--long-name', action='store', dest='long_name', help='asdf',
                 metavar='LONG_NAME'),
            call('--sub-short-name', action='store', dest='sub.short_name', help=None,
                 metavar='SUB_SHORT_NAME'),
            call('--enable', action='store_true', help=None, dest='enable'),
            call('--no-enable', action='store_false', help=None, dest='enable'),
            call('--runtime', action='store', dest='runtime', help=None)
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
            ('x', schema, schema.x),
            ('sub1', schema, schema.sub1),
            ('sub1.y', schema.sub1, schema.sub1.y),
            ('sub1.sub2', schema.sub1, schema.sub1.sub2),
            ('sub1.sub2.z', schema.sub1.sub2, schema.sub1.sub2.z),
            ('sub1.a', schema.sub1, schema.sub1.a),
            ('sub3', schema, schema.sub3),
            ('sub3.b', schema.sub3, schema.sub3.b)
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
            ('x', schema, schema.x),
            ('sub1', schema, schema.sub1),
            ('sub1.y', schema.sub1, schema.sub1.y),
            ('sub1.sub2', schema.sub1, schema.sub1.sub2),
            ('sub1.sub2.z', schema.sub1.sub2, schema.sub1.sub2.z),
            ('sub1.a', schema.sub1, schema.sub1.a),
            ('sub3', schema, schema.sub3),
            ('sub3.b', schema.sub3, schema.sub3.b)
        ]

    def test_make_type(self):
        schema = Schema()
        schema.x = Field(default=2)
        schema.y = Field()

        CustomConfig = make_type(schema, 'CustomConfig')
        cfg = CustomConfig(y=10)
        assert isinstance(cfg, Config)
        assert cfg.x == 2
        assert cfg.y == 10

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

        cmdline_args_override(config, args, ignore=['j'])

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

        cmdline_args_override(config, args, ignore='j')

        assert config.x == '1'
        assert config.y.z == '2'
        assert config.w == 'w'

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
