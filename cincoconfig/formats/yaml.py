#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

try:
    import yaml
except ImportError:  # pragma: no cover
    IS_AVAILABLE = False
else:
    IS_AVAILABLE = True

from cincoconfig.abc import ConfigFormat, BaseConfig


class YamlConfigFormat(ConfigFormat):
    '''
    YAML configuration file format. This format is only available when the ``PyYAML`` package is
    installed.

    This class should not be directly referenced. Instead, use the config
    :meth:`~cincoconfig.Config.load` and :meth:`~cincoconfig.Config.save` methods, passing
    *format='yaml'*.

    .. code-block:: python

        config.save('filename.yml', format='yaml')
        # or
        config.load('filename.yml', format='yaml')
    '''

    def __init__(self, root_key: str = None):
        '''
        By default, the basic value tree is serialized to YAML document as-is, where top-level
        configuration values are placed at the top level of the config file. For example:

        .. code-block:: python

            >>> # assume tree = {'x': 1, 'y': 2}
            >>> print(config.dumps(format='yaml'))
            x: 1
            y: 2

        The *root_key* argument can be specified to store all configuration values under a single
        top-level key:

        .. code-block:: python

            >>> # assume tree = {'x': 1, 'y': 2}
            >>> print(config.dumps(format='yaml', root_key='CONFIG'))
            CONFIG:
                x: 1
                y: 2

        The *root_key* argument affects both how :meth:`loads` and :meth:`dumps` behave.

        :param root_key: the root config key that the configuration values should be stored under
        '''
        if not IS_AVAILABLE:
            raise TypeError('YAML format is not available, please install "PyYAML"')

        self.root_key = root_key

    def dumps(self, config: BaseConfig, tree: dict) -> bytes:
        '''
        Serialize the basic value ``tree`` to YAML :class:`bytes` document. If *root_key* was
        specified, the returned YAML document will contain a single top-level field named
        *root_key* that all other values are stored under.

        :param config: current config
        :param tree: basic value tree
        :returns: the serialized basic value tree
        '''
        if self.root_key:
            tree = {self.root_key: tree}
        return yaml.dump(tree, Dumper=yaml.Dumper).encode()

    def loads(self, config: BaseConfig, content: bytes) -> dict:
        '''
        Deserialize the ``content`` (a :class:`bytes` instance containing a YAML document) to a
        Python basic value tree.  If *root_key* was specified, the returned basic value tree will
        be scoped to *root_key*, if it exists in the deserialized :class:`dict`. This is
        equivalent to:

        .. code-block:: python

            tree = yaml.load(content)
            return tree[self.root_key]

        :param config: current config
        :param content: content to deserialize
        :returns: deserialized basic value tree
        '''
        tree = yaml.load(content.decode(), Loader=yaml.Loader)
        if self.root_key and self.root_key in tree:
            tree = tree[self.root_key]
        return tree
