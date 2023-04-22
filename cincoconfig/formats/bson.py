#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
"""
BSON config file format.
"""
try:
    import bson
except ImportError:  # pragma: no cover
    IS_AVAILABLE = False
else:
    IS_AVAILABLE = True

from ..core import Config, ConfigFormat


class BsonConfigFormat(ConfigFormat):
    """
    BSON configuration file format. This format is only available when the ``bson`` package is
    installed.

    This class should not be directly referenced. Instead, use the config
    :meth:`~cincoconfig.Config.load` and :meth:`~cincoconfig.Config.save` methods, passing
    *format='bson'*.

    .. code-block:: python

        config.save('filename.bson', format='bson')
        # or
        config.load('filename.bson', format='bson')
    """

    def __init__(self):
        if not IS_AVAILABLE:
            raise TypeError('BSON format is not available; please install "bson"')

    def dumps(self, config: Config, tree: dict) -> bytes:
        """
        Serialize the basic value ``tree`` to BSON :class:`bytes` document.

        :param config: current config
        :param tree: basic value tree
        """
        return bson.dumps(tree)

    def loads(self, config: Config, content: bytes) -> dict:
        """
        Deserialize the ``content`` (a :class:`bytes` instance containing a BSON document) to a
        Python basic value tree.

        :param config: current config
        :param content: content to serialize
        :returns: the deserialized basic value tree
        """
        return bson.loads(content)
