#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
import inspect
from typing import Type, Union, Any, Dict
from cincoconfig.abc import Field, BaseSchema
from cincoconfig.config import Config, ConfigType, Schema
from cincoconfig.fields import InstanceMethodField, VirtualField


def get_annotation_typestr(field: Union[Field, BaseSchema, Type, str]) -> str:
    '''
    Get the annotation type string for the provided argument. This method accepts a
    :class:`cincoconfig.Field` and returns the ``storage_type`` annotation.

    :param field: the field, schema, type, or string annotation
    :returns: the annotation type string, or ``typing.Any`` if no annotation is specified.
    '''
    if isinstance(field, Field):
        storage_type = field.storage_type
    elif isinstance(field, BaseSchema):
        storage_type = Schema
    elif isinstance(field, type):
        storage_type = field
    elif isinstance(field, str):
        storage_type = field
    elif field is None:
        storage_type = 'None'
    else:
        raise TypeError('Unknown storage_type: %s' % type(field))

    if isinstance(storage_type, type):
        modname = getattr(storage_type, '__module__', None)
        if modname and modname != 'builtins':
            retval = '%s.%s' % (modname, storage_type.__name__)
        else:
            retval = storage_type.__name__
    else:
        retval = str(storage_type)

    return retval or 'typing.Any'


def get_arg_annotation(key: str, field: Union[Field, BaseSchema, Type, str]) -> str:
    '''
    Get the argument annotation, ``arg: typestr``, for an argument.

    :param key: argument name
    :param field: the argument type
    :returns: the argument annotation
    '''
    typestr = get_annotation_typestr(field)
    return '%s: %s' % (key, typestr)


def get_retval_annotation(annotation: Any) -> str:
    '''
    Get the return value annotation, `` -> typestr``, of the annotation type.

    :param annotation: the return value type or annotation
    :returns: the return value annotation
    '''
    try:
        typestr = get_annotation_typestr(annotation)
    except:
        return ''

    print('retval:', repr(annotation), '-', repr(typestr))
    return ' -> %s' % typestr if typestr else ''


def get_method_annotation(key: str, field: InstanceMethodField) -> str:
    '''
    Get the instance method annotation, ``def key(self, ...): -> typestr: ...``.

    :param key: method name
    :param field: the instance method field
    :returns: the instance method annotation
    '''
    # pylint: disable=too-many-locals
    args, varargs, varkw, _, kwonlyargs, _, annotations = inspect.getfullargspec(field.method)
    has_ret_annotation = 'return' in annotations
    if kwonlyargs:
        if not varargs:
            args.append('*')
        else:
            args.append('*%s' % varargs)
            varargs = None
        args += kwonlyargs

    items = []
    for arg in args:
        has_annotation = arg in annotations
        if has_annotation:
            typestr = get_annotation_typestr(annotations[arg])
        elif not arg.startswith('*'):
            typestr = 'typing.Any'
        else:
            typestr = ''

        if typestr:
            item = '%s: %s' % (arg, typestr)
        else:
            item = arg

        items.append(item)

    if varargs:
        items.append('*%s' % varargs)
    if varkw:
        items.append('**%s' % varkw)

    items[0] = 'self'
    annotation = 'def %s(%s)' % (key, ', '.join(items))
    if has_ret_annotation:
        retval = get_retval_annotation(annotations['return'])
        annotation += retval
    annotation += ': ...'

    return annotation


def generate_stub(config: Union[Schema, ConfigType, Config], class_name: str = None) -> str:
    '''
    Generate the Python stub class (pyi file) for a provided Schema instance, Config instance, or
    ConfigType class. Generating a pyi stub file is useful when developing in an IDE, such as
    VSCode, to make the autocompleter / Intellisense / Language Server understand the structure of
    the configuration and properly show autocomplete results and perform type checking / linting.

    Save the generated pyi stub file to a location in your project repository and then configure
    the IDE / type checked (MyPy) to use the directory to load additional type information from.

    :param config: the configuration to generate the stub file from
    :param class_name: the configuration class name
    :returns: the content of the pyi stub file for the provided configuration
    '''
    if isinstance(config, type) and issubclass(config, ConfigType):
        schema = config.__schema__
        class_name = class_name or config.__name__
    elif isinstance(config, Config):
        schema = config._schema
    elif isinstance(config, Schema):
        schema = config
    else:
        raise TypeError('must be Schema, ConfigType, or Config')

    if not class_name:
        raise TypeError('class_name is required when config is not a ConfigType subclass')

    properties = {}  # type: Dict[str, str]
    methods = {}  # type: Dict[str, InstanceMethodField]
    attrs = {}  # type: Dict[str, str]

    for key, field in schema._fields.items():
        if isinstance(field, VirtualField):
            properties[key] = get_arg_annotation(key, field)
        elif isinstance(field, InstanceMethodField):
            methods[key] = field
        else:
            attrs[key] = properties[key] = get_arg_annotation(key, field)

    blocks = [
        'class %s(cincoconfig.config.ConfigType):' % class_name,
    ] + ['    %s' % attr for attr in properties.values()] + ['']

    attr_list = ['self'] + list(attrs.values())
    blocks.append(
        '    def __init__(%s): ...' % ', '.join(attr_list)
    )

    if methods:
        blocks.append('')

    for key, method_field in methods.items():
        annotation = get_method_annotation(key, method_field)
        blocks.append('    %s' % annotation)

    return '\n'.join(blocks)
