#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Boolean field.
'''
from ..core import Field, Config, FeatureFlagFieldMixin


class BoolField(Field):
    '''
    A boolean field.
    '''
    storage_type = bool
    #: Accepted values that evaluate to ``True``
    TRUE_VALUES = ('t', 'true', '1', 'on', 'yes', 'y')
    #: Accepted values that evaluate to ``False``
    FALSE_VALUES = ('f', 'false', '0', 'off', 'no', 'n')

    def _validate(self, cfg: Config, value: str) -> bool:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''

        if isinstance(value, bool):
            bool_val = value
        elif isinstance(value, (int, float)):
            bool_val = bool(value)
        elif isinstance(value, str):
            if value.lower() in self.TRUE_VALUES:
                bool_val = True
            elif value.lower() in self.FALSE_VALUES:
                bool_val = False
            else:
                raise ValueError('value is not a valid boolean')
        else:
            raise ValueError('value is not a valid boolean')
        return bool_val


class FeatureFlagField(BoolField, FeatureFlagFieldMixin):
    '''
    Concrete implementation of the feature flag field. When this field's value is set to ``False``,
    the bound configurations will not perform validation.
    '''

    def is_feature_enabled(self, cfg: 'Config') -> bool:
        return self.__getval__(cfg)
