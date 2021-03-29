#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Bytes field.
'''
from typing import Any, Optional
import base64
import binascii

from ..core import Field, Config


class BytesField(Field):
    '''
    Store binary data in an encoded string.
    '''
    storage_type = bytes
    #: Available encodings: base64 and hex
    ENCODINGS = ('base64', 'hex')

    def __init__(self, encoding: str = 'base64', **kwargs):
        '''
        :param encoding: binary data encoding, must be one of :attr:`ENCODINGS`
        '''
        super().__init__(**kwargs)

        if encoding not in BytesField.ENCODINGS:
            raise TypeError('invalid encoding: %s' % encoding)
        self.encoding = encoding

    def _validate(self, cfg: Config, value: Any) -> bytes:
        if isinstance(value, str):
            return value.encode()

        if isinstance(value, bytes):
            return value

        raise ValueError('value must be bytes, not %s' % type(value).__name__)

    def to_basic(self, cfg: Config, value: bytes) -> str:
        '''
        :returns: the encoded binary data
        '''
        if value is None:
            return value

        if self.encoding == 'base64':
            return base64.b64encode(value).decode()

        if self.encoding == 'hex':
            return value.hex()

        raise TypeError('invalid encoding: %s' % self.encoding)

    def to_python(self, cfg: Config, value: Any) -> Optional[bytes]:
        '''
        :returns: the decoded binary data
        '''
        if value is None:
            return value

        if not isinstance(value, str):
            raise ValueError('value is not a string')

        if self.encoding == 'base64':
            try:
                ret = base64.b64decode(value)
            except binascii.Error as err:
                raise ValueError('invalid base64 encoding') from err
            else:
                return ret

        if self.encoding == 'hex':
            try:
                ret = bytes.fromhex(value)
            except ValueError as err:
                raise ValueError('invalid hex encoding') from err
            else:
                return ret

        raise TypeError('invalid encoding: %s' % self.encoding)
