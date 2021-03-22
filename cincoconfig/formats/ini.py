#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
INI config file format.
'''
from ..core import ConfigFormat, Config


class IniConfigFormat(ConfigFormat):
    '''
    INI config file format (not implemented yet.)
    '''

    def __init__(self):
        raise NotImplementedError()

    def dumps(self, config: Config, tree: dict) -> bytes:
        raise NotImplementedError()

    def loads(self, config: Config, content: bytes) -> dict:
        raise NotImplementedError()
