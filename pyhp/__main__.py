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
from .main import main, get_args

# get cli arguments
args = get_args()

# execute main with file_path as normal argument and the rest as keyword arguments
sys.exit(main(args.pop("file_path"), **args))
