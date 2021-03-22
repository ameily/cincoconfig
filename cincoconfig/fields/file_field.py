#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
File field.
'''
import os
from typing import Union

from .string_field import StringField
from ..core import Config


class FilenameField(StringField):
    '''
    A field for representing a filename on disk.
    '''
    storage_type = str

    def __init__(self, *, exists: Union[bool, str] = None, startdir: str = None, **kwargs):
        '''
        The *exists* parameter can be set to one of the following values:

        - ``None`` - don't check file's existence
        - ``False`` - validate that the filename does not exist
        - ``True`` - validate that the filename does exist
        - ``"dir"`` - validate that the filename is a directory that exists
        - ``"file"`` - validate that the filename is a file that exists

        The *startdir* parameter, if specified, will resolve filenames starting from a directory
        and will cause all filenames to be validate to their abslute file path. If not specified,
        filename's will be resolve relative to :meth:`os.getcwd` and the relative file path will
        be validated.

        :param exists: validate the filename's existence on disk
        :param startdir: resolve relative paths to a start directory
        '''
        super().__init__(**kwargs)
        self.exists = exists
        self.startdir = startdir

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''
        value = super()._validate(cfg, value)

        if not value:
            return value

        if not os.path.isabs(value) and self.startdir:
            value = os.path.abspath(os.path.expanduser(os.path.join(self.startdir, value)))

        if os.path.sep == '\\':
            value = value.replace('/', '\\')

        value_exists = os.path.exists(value)
        if self.exists is True and not value_exists:
            raise ValueError('file or directory does not exist: %s' % value)
        if self.exists is False and value_exists:
            raise ValueError('file or directory already exists: %s' % value)
        if self.exists == 'dir' and not os.path.isdir(value):
            raise ValueError('directory %s: %s' %
                             ('already exists' if value_exists else 'does not exist', value))
        if self.exists == 'file' and not os.path.isfile(value):
            raise ValueError('file %s: %s' %
                             ('already exists' if value_exists else 'does not exist', value))

        return value
