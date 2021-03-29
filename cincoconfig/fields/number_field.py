#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Number fields
'''
from typing import Union

from ..core import Field, Config


class NumberField(Field):
    '''
    Base class for all number fields. This field should not be used directly, instead consider
    using :class:`~cincoconfig.IntField` or :class:`~cincoconfig.FloatField`.
    '''

    def __init__(self, type_cls: type, *, min: Union[int, float] = None,
                 max: Union[int, float] = None, **kwargs):
        '''
        :param type_cls: number type class that values will be converted to
        :param min: minimum value (inclusive)
        :param max: maximum value (inclusive)
        '''
        super().__init__(**kwargs)
        self.type_cls = type_cls
        self.min = min
        self.max = max
        self.storage_type = type_cls

    def _validate(self, cfg: Config, value: Union[str, int, float]) -> Union[int, float]:
        '''
        Validate the value. This method first converts the value to ``type_class`` and then checks
        the value against ``min`` and ``max`` if they are specified.

        :param cfg: current Config
        :param value: value to validate
        '''
        if not isinstance(value, (str, int, float, self.type_cls)) or isinstance(value, bool):
            raise ValueError('value type %s cannot be converted to %s' %
                             (type(value).__name__, self.type_cls.__name__))

        try:
            num = self.type_cls(value)  # type: Union[int, float]
        except (ValueError, TypeError) as err:
            raise ValueError('value is not a valid %s' % self.type_cls.__name__) from err

        if self.min is not None and num < self.min:
            raise ValueError('value must be >= %s' % self.min)

        if self.max is not None and num > self.max:
            raise ValueError('value must be <= %s' % self.max)

        return num


class IntField(NumberField):
    '''
    Integer field.
    '''
    storage_type = int

    def __init__(self, **kwargs):
        super().__init__(int, **kwargs)


class FloatField(NumberField):
    '''
    Float field.
    '''
    storage_type = float

    def __init__(self, **kwargs):
        super().__init__(float, **kwargs)
