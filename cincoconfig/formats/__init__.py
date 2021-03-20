#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
from typing import List, Tuple, Type

from ..core import ConfigFormat
from .json import JsonConfigFormat
from .pickle import PickleConfigFormat
from .xml import XmlConfigFormat
from .yaml import YamlConfigFormat, IS_AVAILABLE as YAML_IS_AVAILABLE
from .bson import BsonConfigFormat, IS_AVAILABLE as BSON_IS_AVAILABLE


FORMATS: List[Tuple[str, Type[ConfigFormat]]] = [
    ('json', JsonConfigFormat),
    ('pickle', PickleConfigFormat),
    ('xml', XmlConfigFormat),
]

if YAML_IS_AVAILABLE:
    FORMATS.append(('yaml', YamlConfigFormat))
if BSON_IS_AVAILABLE:
    FORMATS.append(('bson', BsonConfigFormat))
