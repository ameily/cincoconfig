#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
from typing import Type, Union
from cincoconfig.config import Schema, ConfigType
from cincoconfig.abc import SchemaField
from cincoconfig.fields import InstanceMethodField, VirtualField


def get_annotation_type(field: SchemaField) -> str:
    '''
    Get the annotation type of the field by checking the storage_type.

    :param field: field to get the annotation type
    :return: the annotation type
    '''
    storage_type = getattr(field, 'storage_type', type(field))
    if isinstance(storage_type, type):
        if storage_type.__module__ and storage_type.__module__ != 'builtins':
            storage_type = '.'.join([storage_type.__module__, storage_type.__name__])
        else:
            storage_type = storage_type.__name__
    return str(storage_type)


def generate_stub(schema: Union[Schema, Type[ConfigType]], type_name: str = None) -> str:
    '''
    Generate the stub python for the schema or config type. This method is useful to generate PYI
    stub files so IDEs can autocomplete configuration files.

    :param schema: the schema or config type
    :param type_name: the configuration type name (class name)
    :returns: the stub PYI file
    '''
    methods = {}
    properties = {}
    allprops = {}

    if isinstance(schema, Schema):
        if not type_name:
            raise TypeError('type_name is required')
    elif issubclass(schema, ConfigType):
        type_name = type_name or schema.__name__
    else:
        raise TypeError('schema must be a Schema instance or ConfigType subclass')

    for key, field in schema:
        if isinstance(field, VirtualField):
            allprops[key] = field
        elif isinstance(field, InstanceMethodField):
            methods[key] = field
        else:
            allprops[key] = properties[key] = field

    init_args = ', '.join(['{}: {}'.format(key, get_annotation_type(field))
                           for key, field in properties.items()])
    init_meth = '    def __init__(self, {}): ...'.format(init_args)

    property_annotations = '\n'.join(['    {}: {}'.format(key, get_annotation_type(field))
                                      for key, field in allprops.items()])
    blocks = ['class {}(ConfigType):'.format(type_name), property_annotations, init_meth]
    if methods:
        blocks.append('\n'.join(['    def {}(self, *args, **kwargs): ...'.format(key)
                                 for key in methods]))

    return '\n\n'.join(blocks)
