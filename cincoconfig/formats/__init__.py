#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
"""
Built-in config file formats.
"""
from typing import List, Tuple, Type

from ..core import ConfigFormat
from .bson import IS_AVAILABLE as BSON_IS_AVAILABLE
from .bson import BsonConfigFormat
from .json import JsonConfigFormat
from .pickle import PickleConfigFormat
from .xml import XmlConfigFormat
from .yaml import IS_AVAILABLE as YAML_IS_AVAILABLE
from .yaml import YamlConfigFormat

#: List of built-in available config file formats.
FORMATS: List[Tuple[str, Type[ConfigFormat]]] = [
    ("json", JsonConfigFormat),
    ("pickle", PickleConfigFormat),
    ("xml", XmlConfigFormat),
]

if YAML_IS_AVAILABLE:
    FORMATS.append(("yaml", YamlConfigFormat))
if BSON_IS_AVAILABLE:
    FORMATS.append(("bson", BsonConfigFormat))
