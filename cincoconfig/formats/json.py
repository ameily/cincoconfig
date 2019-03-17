#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import json
from cincoconfig.abc import ConfigFormat
from cincoconfig.config import Config, Schema


class JsonConfigFormat(ConfigFormat):

    def __init__(self, pretty: bool = True):
        self.pretty = pretty
        self.is_binary = False

    def dumps(self, schema: Schema, config: Config, tree: dict) -> str:
        return json.dumps(tree, index=2 if self.pretty else None)

    def loads(self, schema: Schema, config: Config, content: str) -> dict:
        return json.loads(content)
