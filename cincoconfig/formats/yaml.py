#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

try:
    import yaml
except ImportError:  # pylint: disable=duplicate-code
    IS_AVAILABLE = False
else:
    IS_AVAILABLE = True

from cincoconfig.abc import ConfigFormat
from cincoconfig.config import Config, Schema


class YamlConfigFormat(ConfigFormat):
    is_binary = False

    def __init__(self, root_key: str = None):
        if not IS_AVAILABLE:
            raise TypeError('YAML format is not available, please install "PyYAML"')

        self.root_key = root_key

    def dumps(self, schema: Schema, config: Config, tree: dict) -> str:
        if self.root_key:
            tree = {self.root_key: tree}
        return yaml.dump(tree)

    def loads(self, schema: Schema, config: Config, content: str) -> dict:
        tree = yaml.load(content)
        if self.root_key and self.root_key in tree:
            tree = tree[self.root_key]
        return tree
