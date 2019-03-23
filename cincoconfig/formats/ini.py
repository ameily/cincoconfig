#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from cincoconfig.abc import ConfigFormat, BaseConfig


class IniConfigFormat(ConfigFormat):

    def __init__(self):
        raise NotImplementedError()

    def dumps(self, config: BaseConfig, tree: dict) -> bytes:
        raise NotImplementedError()

    def loads(self, config: BaseConfig, content: bytes) -> dict:
        raise NotImplementedError()
