#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Any
import xml.etree.ElementTree as ET
from cincoconfig.abc import ConfigFormat
from cincoconfig.config import Config, Schema


class XmlConfigFormat(ConfigFormat):
    is_binary = False

    def __init__(self, root_element: str = 'config'):
        self.root_element = root_element or 'config'

    def _to_element(self, name: str, value: Any) -> ET.Element:
        ele = ET.Element(name)
        if isinstance(value, list):
            for item in value:
                ele.append(self._to_element(name, item))
        elif isinstance(value, dict):
            for key, val in value.items():
                ele.append(self._to_element(key, val))
        elif value is None:
            ele.text = ''
        else:
            ele.text = str(value)

        return ele

    def dumps(self, schema: Schema, config: Config, tree: dict) -> str:
        return self._to_element(tree, config._key)

    def loads(self, schema: Schema, config: Config, content: str) -> dict:
        raise NotImplementedError()
