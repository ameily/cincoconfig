#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
"""
Cincoconfig Public API
"""
# ruff: noqa: F401
from .core import (
    AnyField,
    Config,
    ConfigFormat,
    ConfigType,
    Field,
    Schema,
    ValidationError,
)
from .encryption import KeyFile
from .fields import *  # noqa: F403
from .stubs import generate_stub
from .support import (
    asdict,
    cmdline_args_override,
    generate_argparse_parser,
    get_all_fields,
    get_fields,
    is_value_defined,
    item_ref_path,
    make_type,
    reset_value,
    validator,
)
from .version import __version__

# DEPRECATED TYPE ALIASES
BaseConfig = Config
BaseSchema = Schema
