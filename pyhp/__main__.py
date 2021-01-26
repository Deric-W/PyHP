#!/usr/bin/python3

"""Script to support python3 -m pyhp"""
# This script is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

import sys
from .main import main, argparser

# get cli arguments
args = argparser.parse_args()

# execute main
sys.exit(
    main(
        args.file,
        args.caching,
        args.config
    )
)
