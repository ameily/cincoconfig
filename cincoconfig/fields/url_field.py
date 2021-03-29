#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
URL field.
'''
from urllib.parse import urlparse

from .string_field import StringField
from ..core import Config


class UrlField(StringField):
    '''
    A URL field. Values are validated that they are both a valid URL and contain a valid scheme.
    '''
    storage_type = str

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate the value.

        :param cfg: current config
        :param value: value to validate
        '''
        value = super()._validate(cfg, value)

        try:
            url = urlparse(value)
            if not url.scheme:
                raise ValueError('no scheme url scheme')
        except Exception as err:
            raise ValueError('value is not a valid URL') from err
        return value
