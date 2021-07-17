#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Cincoconfig Public API
'''
from .core import Config, Field, Schema, ValidationError, AnyField, ConfigFormat, ConfigType
from .support import (make_type, validator, get_all_fields, generate_argparse_parser,
                      item_ref_path, cmdline_args_override, asdict, get_fields)
from .fields import *
from .encryption import KeyFile
from .stubs import generate_stub
from .version import __version__

# DEPRECATED TYPE ALIASES
BaseConfig = Config
BaseSchema = Schema
