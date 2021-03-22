#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Cincoconfig Public API
'''
from .core import Config, Field, Schema, ValidationError, AnyField, ConfigFormat
from .support import make_type, validator, get_all_fields, generate_argparse_parser
from .fields import *
from .encryption import KeyFile
from .stubs import generate_stub
from .version import __version__

# DEPRECATED TYPE ALIASES
BaseConfig = Config
BaseSchema = Schema
