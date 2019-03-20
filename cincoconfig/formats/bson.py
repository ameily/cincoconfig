#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

try:
    import bson
except ImportError:  # pylint: disable=duplicate-code
    IS_AVAILABLE = False
else:
    IS_AVAILABLE = True

from cincoconfig.abc import ConfigFormat
from cincoconfig.config import Config, Schema


class BsonConfigFormat(ConfigFormat):
    is_binary = True

    def __init__(self):
        if not IS_AVAILABLE:
            raise TypeError('BSON format is not available; please install "bson"')

    def dumps(self, schema: Schema, config: Config, tree: dict) -> bytes:
        return bson.dumps(tree)

    def oads(self, schema: Schema, config: Config, content: bytes) -> dict:
        return bson.loads(content)
