#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
"""
Python pickle binary config file format.
"""
import pickle

from ..core import Config, ConfigFormat


class PickleConfigFormat(ConfigFormat):
    """
    Python pickle configuration file format. This format uses the :mod:`pickle` module to serialize
    and deserialize the configuration basic value tree.

    This class should not be directly referenced. Instead, use the config
    :meth:`~cincoconfig.Config.load` and :meth:`~cincoconfig.Config.save` methods, passing
    *format='pickle'*.

    .. code-block:: python

        config.save('filename.cfg', format='pickle')
        # or
        config.load('filename.cfg', format='pickle')
    """

    def dumps(self, config: Config, tree: dict) -> bytes:
        """
        Deserialize the ``content`` (a :class:`bytes` instance containing a Pickled object) to a
        Python basic value tree.

        :param config: current config
        :param content: content to serialize
        :returns: the deserialized basic value tree
        """
        return pickle.dumps(tree)

    def loads(self, config: Config, content: bytes) -> dict:
        """
        Serialize the basic value ``tree`` to PIckle :class:`bytes` document.

        :param config: current config
        :param tree: basic value tree
        """
        return pickle.loads(content)
