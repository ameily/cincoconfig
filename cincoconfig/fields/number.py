#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Cinco Config Fields.
'''

from typing import Union
from cincoconfig.abc import Field
from cincoconfig.config import Config


__all__ = ('IntField', 'FloatField', 'PortField', 'NumberField')


class NumberField(Field):
    '''
    Base class for all number fields. This field should not be used directly, instead consider
    using :class:`~cincoconfig.IntField` or :class:`~cincoconfig.FloatField`.
    '''

    def __init__(self, type_cls: type, *, min: Union[int, float] = None,
                 max: Union[int, float] = None, **kwargs):
        '''
        :param type_cls: number type class that values will be converted to
        :param min: minimum value
        :param max: maxium value
        '''
        super().__init__(**kwargs)
        self.type_cls = type_cls
        self.min = min
        self.max = max

    def _validate(self, cfg: Config, value: Union[str, int, float]) -> Union[int, float]:
        '''
        Validate the value. This method first converts the value to ``type_class`` and then checks
        the value against ``min`` and ``max`` if they are specified.

        :param cfg: current Config
        :param value: value to validate
        '''
        try:
            value = self.type_cls(value)
        except:
            raise ValueError('%s is not a valid %s' % (self.name, self.type_cls.__name__))

        if self.min is not None and value < self.min:
            raise ValueError('%s must be >= %s' % (self.name, self.min))

        if self.max is not None and value > self.max:
            raise ValueError('%s must be <= %s' % (self.name, self.max))

        return value


class IntField(NumberField):
    '''
    Integer field.
    '''

    def __init__(self, **kwargs):
        super().__init__(int, **kwargs)


class FloatField(NumberField):
    '''
    Float field.
    '''

    def __init__(self, **kwargs):
        super().__init__(float, **kwargs)


class PortField(IntField):
    '''
    Network port field.
    '''

    def __init__(self, **kwargs):
        kwargs.setdefault('min', 1)
        kwargs.setdefault('max', 65535)
        super().__init__(**kwargs)
