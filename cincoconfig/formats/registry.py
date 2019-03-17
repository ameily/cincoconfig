#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#


class FormatRegistry:
    _formats = dict()
    _initialized = False

    @classmethod
    def get(cls, name: str, **kwargs):
        if not cls._initialized:
            cls._init()
        fmt = cls._formats.get(name.lower())
        return fmt(**kwargs) if fmt else None

    @classmethod
    def registry(cls, name: str, format_cls):
        cls._formats[name] = format_cls

    @classmethod
    def _init(cls):
        # pylint: disable=cyclic-import
        if not cls._initialized:
            from .ini import IniConfigFormat
            from .json import JsonConfigFormat
            from .yaml import YamlConfigFormat
            from .xml import XmlConfigFormat
            cls._formats.update({
                'json': JsonConfigFormat,
                'xml': XmlConfigFormat,
                'yaml': YamlConfigFormat,
                'ini': IniConfigFormat
            })
            cls._initialized = True
