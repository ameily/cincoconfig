#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Type
from cincoconfig import abc


class FormatRegistry:
    __formats = dict()
    __initialized = False

    @classmethod
    def get(cls, name: str, **kwargs) -> abc.ConfigFormat:
        if not cls.__initialized:
            cls.__initialize()
        fmt = cls.__formats.get(name.lower())
        if not fmt:
            raise KeyError('unrecognized format: %s' % name)
        return fmt(**kwargs)

    @classmethod
    def register(cls, name: str, format_cls: Type[abc.ConfigFormat]):
        if not cls.__initialized:
            cls.__initialize()
        cls.__formats[name] = format_cls

    @classmethod
    def __initialize(cls):
        # pylint: disable=cyclic-import
        if not cls.__initialized:
            from .ini import IniConfigFormat
            from .json import JsonConfigFormat
            from .xml import XmlConfigFormat
            from . import yaml
            from . import bson
            cls.__formats.update({
                'json': JsonConfigFormat,
                'xml': XmlConfigFormat,
                'ini': IniConfigFormat
            })

            if yaml.IS_AVAILABLE:
                cls.__formats['yaml'] = yaml.YamlConfigFormat
            if bson.IS_AVAILABLE:
                cls.__formats['bson'] = bson.BsonConfigFormat
            cls.__initialized = True
