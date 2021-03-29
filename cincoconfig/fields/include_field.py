#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Include field.
'''
import os

from .file_field import FilenameField
from ..core import Config, ConfigFormat, IncludeFieldMixin


class IncludeField(FilenameField, IncludeFieldMixin):
    '''
    A special field that can include another configuration file when loading from disk. Included
    files are in the same scope as where the include field is defined for example:

    .. code-block:: yaml

        # file1.yaml
        db:
          include: "db.yaml"
        include: "core.yaml"

        # db.yaml
        host: "0.0.0.0"
        port: 27017

        # core.yaml
        mode: "production"
        ssl: true

    The final parsed configuration would be equivalent to:

    .. code-block:: yaml

        db:
          host: "0.0.0.0"
          port: 27017

        mode: "production"
        ssl: true

    Included files must be in the same configuration file format as their parent file. So,
    if the base configuration file is stored in JSON then every included file must also be in JSON.

    Cincoconfig does not track which configuration file set which field(s). When a config file is
    saved back to disk, it will be the entire configuration, even if it was originally defined
    across multiple included files.
    '''

    def __init__(self, startdir: str = None, **kwargs):
        '''
        :param startdir: resolve relative include paths to a start directory
        '''
        super().__init__(exists='file', startdir=startdir, **kwargs)

    def include(self, config: Config, fmt: ConfigFormat, filename: str, base: dict) -> dict:
        '''
        Include a configuration file and combine it with an already parsed basic value tree. Values
        defined in the included file will overwrite values in the base tree. Nested trees (``dict``
        objects) will be combined using a :meth:`dict.update` like method, :meth:`combine_trees`.

        :param config: configuration object
        :param fmt: configuration file format that will parse the included file
        :param filename: included file path
        :param base: base config value tree
        :returns: the new basic value tree containing the base tree and the included tree
        '''
        filename = self.validate(config, filename)
        with open(os.path.expanduser(filename), 'rb') as fp:
            content = fp.read()

        child = fmt.loads(config, content)
        return self.combine_trees(base, child)

    def combine_trees(self, base: dict, child: dict) -> dict:
        '''
        An extension to :meth:`dict.update` but properly handles nested `dict` objects.

        :param base: base tree to extend
        :param child: child tree to apply onto base
        :returns: the new combined ``dict``
        '''
        ret = dict(base)
        for key, value in child.items():
            if key in base:
                base_value = base[key]
                if isinstance(base_value, dict) and isinstance(value, dict):
                    ret[key] = self.combine_trees(base_value, value)
                else:
                    ret[key] = value
            else:
                ret[key] = value

        return ret
