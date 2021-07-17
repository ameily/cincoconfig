#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Support functions.
'''
import sys
from argparse import ArgumentParser, Namespace
from typing import Callable, List, Tuple, Union, Type
from .core import (Schema, BaseField, Config, ConfigType, FieldValidator, ConfigValidator, Field,
                   VirtualFieldMixin)


def make_type(schema: Schema, name: str, module: str = None,
              key_filename: str = None) -> Type[ConfigType]:
    '''
    Create a new type that wraps this schema. This method should only be called once per
    schema object.

    Use this method when to create reusable configuration objects that can be used multiple
    times  in code in a more traditional Pythonic manner. For example, consider the following:

    .. code-block:: python

        item_schema = Schema()
        item_schema.url = UrlField()
        item_schema.verify_ssl = BoolField(default=True)

        schema = Schema()
        schema.endpoints = ListField(item_schema)

        config = schema()

        # to create new web hook items
        item = webhook_schema()
        item.url = 'https://google.com'
        item.verify_ssl = False

        config.endpoints.append(item)

    This is a cumbersome design when creating these objects within code. ``make_type`` will
    dynamically create a new class that can be used in a more Pythonic way:

    .. code-block:: python

        # same schema as above
        config = schema()
        Item = make_type(item_schema, 'Item')

        item = Item(url='https://google.com', verify_ssl=False)
        config.endpoints.append(item)

    The new class inherits from :class:`Config`.

    :param name: the new class name
    :param module: the owning module
    :param key_filename: the key file name passed to each new config object,
    :param validator: config validator callback method
    :returns: the new type
    '''
    result = type(name, (ConfigType,), {
        '__schema__': schema,
        '__key_filename__': key_filename
    })
    # This is copied from the namedtuple method. We try to set the module of the new
    # class to the calling module.
    if module is None:
        try:
            module = sys._getframe(1).f_globals.get('__name__', '__main__')
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    if module is not None:
        result.__module__ = module

    return result


def generate_argparse_parser(schema, **parser_kwargs) -> ArgumentParser:
    '''
    Generate a :class:`argparse.ArgumentParser` based on the schema. This method generates
    ``--long-arguments`` for each field that stores a string, integer, float, or bool (based
    on the field's ``storage_type``). Boolean fields have two long arguments created, one to
    store a ``True`` value and another, ``--no-[x]``, to disable it.

    :param kwargs: keyword arguments to pass to the generated ``ArgumentParser`` constructor
    :returns: the generated argument parser
    '''
    parser = ArgumentParser(**parser_kwargs)
    for name, _, field in get_all_fields(schema):
        if not isinstance(field, Field):
            continue

        arg = '--' + name.replace('.', '-').replace('_', '-').lower()
        metavar = name.replace('.', '_').upper()
        if field.storage_type in (str, float, int):
            parser.add_argument(arg, action='store', dest=name, help=field.short_help,
                                metavar=metavar)
        elif field.storage_type is bool:
            off_arg = '--no-' + name.replace('.', '-').replace('_', '-').lower()
            parser.add_argument(arg, dest=name, action='store_true', help=field.short_help)
            parser.add_argument(off_arg, dest=name, action='store_false')

    return parser


def validator(field: BaseField) -> Callable:
    '''
    Decorator to register a new validator with the schema or field. All validators will be run
    against the configuration whenever the configuration is loaded from disk. Multiple validators
    can be registered by using the decorator multiple times. Subconfigs can also be validated by
    using the decorator on the sub schema.

    .. code-block:: python

        schema = Schema()
        schema.x = IntField()
        schema.y = IntField()
        schema.db.username = StringField()
        schema.db.password = StringField()

        @validator(schema)
        def validate_x_lt_y(cfg):
            if cfg.x and cfg.y and cfg.x >= cfg.y:
                raise ValueError('x must be less-than y')

        @validator(schema.db)
        def validate_db_credentials(cfg):
            if cfg.username and not db.password:
                raise ValueError('db.password is required when username is specified')

        config = schema()
        config.load('config.json', format='json')  # will call the above validators
        # .....

    The validator function needs to raise an exception, preferably a :class:`ValueError`, if
    the validation fails.

    :param func: validator function that accepts a single argument: :class:`Config`.
    :returns: ``func``
    '''
    def inner(func: Union[ConfigValidator, FieldValidator]) -> Callable:
        if isinstance(field, Field):
            field.validator = func  # type: ignore
        elif isinstance(field, Schema):
            field._validators.append(func)  # type: ignore

        return func

    return inner


def get_all_fields(schema: Union[Schema, Config]) -> List[Tuple[str, Schema, BaseField]]:
    '''
    Get all the fields and nested fields of the schema or config, including the nested
    schemas/configs.

    .. code-block:: python

        >>> schema = Schema()
        >>> schema.x = IntField()
        >>> schema.y.z = StringField()
        >>> schema.z = StringField()
        >>> get_all_fields(schema)
        [
            ('x', schema, schema.x),
            ('y.z', schema.y, schema.y.z),
            ('z', schema, schema.z)
        ]

    The returned list of tuples have three values:

    1. `path` - the full path to the field.
    2. `schema` - the schema that the field belongs to.
    3. `field` - the field.

    The order of the fields will be the same order in which the fields were added to the
    schema.

    :returns: all the fields as a list of tuples: ``(path, schema, field)``
    '''
    if isinstance(schema, Config):
        schema = schema._schema

    ret = []
    prefix = schema._key + '.' if schema._key else ''
    for key, field in schema._fields.items():
        ret.append((prefix + key, schema, field))
        if isinstance(field, Schema):
            ret.extend([(prefix + subkey, schema, subfield)
                        for subkey, schema, subfield in get_all_fields(field)])
    return ret


def cmdline_args_override(config: Config, args: Namespace,
                          ignore: Union[str, List[str]] = None) -> None:
    '''
    Override configuration setting based on command line arguments, parsed from the
    :mod:`argparse` module. This method is useful when loading a configuration but allowing the
    user the option to override or extend the configuration via command line arguments.

    .. code-block:: python

        parser = argparse.ArgumentParser()
        parser.add_argument('-d', '--debug', action='store_const', const='debug', dest='mode')
        parser.add_argument('-p', '--port', action='store', dest='http.port')
        parser.add_argument('-H', '--host', action='store', dest='http.address')
        parser.add_argument('-c', '--config', action='store')

        args = parser.parse_args()
        if args.config:
            config.load(args.config, format='json')

        config.cmdline_args_override(args, ignore=['config'])

        # cmdline_args_override() is equivalent to doing:

        if args.mode:
            config.mode = args.mode
        if getattr(args, 'http.port'):
            config.http.port = getattr(args, 'http.port')
        if getattr(args, 'http.address'):
            config.http.address = getattr(args, 'http.address')

    This method is compatible with manually created argument parser and an autogenerated one
    from the Schema :meth:`~Schema.generate_argparse_parser` method.

    :param args: parsed command line arguments from :meth:`~argparse.ArgumentParser.parse_args`
    :param ignore: list of arguments to ignore and not process
    '''
    if isinstance(ignore, str):
        ignore = [ignore]
    else:
        ignore = ignore or []

    for key, value in vars(args).items():
        if key not in ignore and value is not None:
            config.__setitem__(key, value)


def item_ref_path(item: Union[BaseField, Config]) -> str:
    '''
    Get the full reference path to a field or configuration.

    :param item: field, schema, or configuration
    :returns: full reference path to the item
    '''
    return item._ref_path


def get_fields(schema: Union[Config, Schema],
               types: Union[Type, Tuple[Type]] = None) -> List[Tuple[str, BaseField]]:
    '''
    Get all fields within a configuration or schema. This method does not recurse into nested
    schemas/configs, unlike :meth:`~get_all_fields`. The return value is a list of fields as tuples
    ``(key, field)``.

    :param schema: schema or configuration object
    :param types: only return fields of a specific type
    :returns: the list of fields
    '''

    fields = list(schema._fields.items())
    if isinstance(schema, Config):
        fields += list(schema._schema._fields.items())

    if types:
        fields = [item for item in fields if isinstance(item[1], types)]
    return fields


def _list_asdict(items: list, virtual: bool) -> list:
    '''
    Handle nested lists and nested Config object for :meth:`asdict`.

    :param items: list
    :param virtual: include configuration virtual values
    :returns: converted list
    '''
    value = []
    for item in items:
        if isinstance(item, list):
            item = _list_asdict(item, virtual=virtual)
        elif isinstance(item, Config):
            item = asdict(item, virtual=virtual)
        elif isinstance(item, dict):
            item = dict(item)
        value.append(item)
    return value


def asdict(config: Config, virtual: bool = False) -> dict:
    '''
    Converts the configuration object to a dict. Whereas :meth:`~Config.to_tree` converts the
    configuration to a basic value tree suitable for saving to disk, the ``asdict`` method converts
    the configuration, and all nested configuration objects, to a dict, preserving each value
    as-is.

    :param config: the configuration to conver to a dict
    :param virtual: include virtual field values in the dict
    :returns: the converted configuration dict
    '''
    data = {}
    for key, value in config._data.items():
        if isinstance(value, list):
            value = _list_asdict(value, virtual=virtual)
        elif isinstance(value, Config):
            value = asdict(value, virtual=virtual)
        elif isinstance(value, dict):
            value = dict(value)
        data[key] = value

    if virtual:
        fields = get_fields(config, VirtualFieldMixin)
        data.update({key: field.__getval__(config) for key, field in fields})

    return data
