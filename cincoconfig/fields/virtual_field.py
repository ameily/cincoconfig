#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Virtual field
'''
from typing import Callable, Any

from ..core import Field, VirtualFieldMixin, Config


class VirtualField(Field, VirtualFieldMixin):
    '''
    A calculated, readonly field that is not read from or written to a configuration file.
    '''

    def __init__(self, getter: Callable[[Config], Any],
                 setter: Callable[[Config, Any], Any] = None, **kwargs):
        '''
        :param getter: a callable that is called whenever the value is retrieved, the callable
            will receive a single argument: the current :class:`Config`.
        :param setter: a callable that is called whenever the value is set, the callable will
            receive two arguments: ``config, value``, the current :class:`Config` and the value
            being set
        '''
        if kwargs.get('default') is not None:
            raise TypeError('virtual fields cannot have a default value')

        super().__init__(**kwargs)
        self.getter = getter
        self.setter = setter

    def __setdefault__(self, cfg: Config) -> None:
        pass

    def __getval__(self, cfg: Config) -> Any:
        return self.getter(cfg)

    def __setval__(self, cfg: Config, value: Any) -> None:
        if not self.setter:
            raise TypeError('field is readonly')
        self.setter(cfg, value)
