#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
"""
Cincoconfig version.
"""
from pathlib import Path

__version__ = (Path(__file__).parent / "VERSION").read_text().strip()
