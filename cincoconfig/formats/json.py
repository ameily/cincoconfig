#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
JSON config file format.
'''
import json
from ..core import ConfigFormat, Config


class JsonConfigFormat(ConfigFormat):
    '''
    JSON configuration file format.

    This class should not be directly referenced. Instead, use the config
    :meth:`~cincoconfig.Config.load` and :meth:`~cincoconfig.Config.save` methods, passing
    *format='json'*.

    .. code-block:: python

        config.save('filename.json', format='json')
        # or
        config.load('filename.json', format='json')
    '''

    def __init__(self, pretty: bool = True):
        '''
        :param pretty: pretty-print the JSON document in the call to :meth:`json.dumps`
        '''
        self.pretty = pretty

    def dumps(self, config: Config, tree: dict) -> bytes:
        '''
        Deserialize the ``content`` (a :class:`bytes` instance containing a JSON document) to a
        Python basic value tree.

        :param config: current config
        :param content: content to serialize
        :returns: the deserialized basic value tree
        '''
        return json.dumps(tree, indent=2 if self.pretty else None).encode()

    def loads(self, config: Config, content: bytes) -> dict:
        '''
        Serialize the basic value ``tree`` to JSON :class:`bytes` document.

        :param config: current config
        :param tree: basic value tree
        '''
        return json.loads(content.decode())
