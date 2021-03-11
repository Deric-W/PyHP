#!/usr/bin/python3

"""Package containing timestamp-based caches"""
# The backends.caches.timestamped package is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

import time


__all__ = (
    "check_mtime",
    "files",
    "memory"
)


def check_mtime(s_mtime: int, c_mtime: int, ttl: int = 0) -> bool:
    """check if a timestamp is valid"""
    if c_mtime < s_mtime:  # outdated
        return False
    if ttl > 0:    # up to date, check ttl
        return ttl > (time.time_ns() - c_mtime)
    return True    # up to date
