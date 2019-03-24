#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Type, Dict
from ..abc import ConfigFormat
from .json import JsonConfigFormat
from .pickle import PickleConfigFormat
from .xml import XmlConfigFormat
from .yaml import YamlConfigFormat, IS_AVAILABLE as YAML_IS_AVAILABLE
from .bson import BsonConfigFormat, IS_AVAILABLE as BSON_IS_AVAILABLE


class _FormatRegistrySingleton:
    '''
    The format registry singleton that holds all available config formats. The singleton instance
    is avialable via

    .. code-block:: python

        from cincoconfig import FormatRegistry

    The FormatRegistry automatically registers the builtin formats:

    - ``bson`` - :class:`~cincoconfig.formats.BsonConfigFormat`
    - ``json`` - :class:`~cincoconfig.formats.JsonConfigFormat`
    - ``pickle`` - :class:`~cincoconfig.formats.PickleConfigFormat`
    - ``xml`` - :class:`~cincoconfig.formats.XmlConfigFormat`
    - ``yaml`` - :class:`~cincoconfig.formats.YamlConfigFormat`
    '''

    def __init__(self):
        self._formats = dict()  # type: Dict[str, Type[ConfigFormat]]
        self._initialized = False

    def get(self, name: str, **kwargs) -> ConfigFormat:
        '''
        Get and instantiate the configuration format identified by *name*, passing *kwargs* to the
        format's constructor.

        :param name: config format name, used when the format was registered.
        :raises KeyError: the config format is not registered
        :returns: the instantiated config format
        '''
        if not self._initialized:
            self._initialize()

        fmt = self._formats.get(name.lower())
        if not fmt:
            raise KeyError('unrecognized format: %s' % name)
        return fmt(**kwargs)  # type: ignore

    def register(self, name: str, format_cls: Type[ConfigFormat]) -> None:
        '''
        Register a new config format.

        :param name: config format name
        :param format_cls: the class that handles the format
        '''
        if not self._initialized:
            self._initialize()
        self._formats[name] = format_cls

    def _initialize(self) -> None:
        '''
        Initialize the builtin formats.
        '''
        if not self._initialized:

            self._formats.update({
                'json': JsonConfigFormat,
                'pickle': PickleConfigFormat,
                'xml': XmlConfigFormat
            })

            if YAML_IS_AVAILABLE:
                self._formats['yaml'] = YamlConfigFormat
            if BSON_IS_AVAILABLE:
                self._formats['bson'] = BsonConfigFormat
            self._initialized = True


FormatRegistry = _FormatRegistrySingleton()  # pylint: disable=C0103
