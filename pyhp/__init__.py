#!/usr/bin/python3

"""Package for embedding and using python code like php"""
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

# package metadata
# needs to be defined before .main is imported
__version__ = "3.0"
__author__ = "Eric Wolf"
__maintainer__ = "Eric Wolf"
__license__ = "GPLv3"
__email__ = "robo-eric@gmx.de"  # please dont use for spam :(
__contact__ = "https://github.com/Deric-W/PyHP"

__all__ = (
    "compiler",
    "backends",
    "wsgi",
    "main",
    "config"
)
