#!/usr/bin/python3

"""Module containing configuration utilities"""
# The config module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

import os
import os.path
from typing import Any, Iterable, MutableMapping
import toml

__all__ = (
    "CONFIG_LOCATIONS",
    "load_config"
)

CONFIG_LOCATIONS = (
    os.path.expanduser("~/.config/pyhp.toml"),
    "/etc/pyhp.toml"
)


def load_config(search_paths: Iterable[str] = CONFIG_LOCATIONS) -> MutableMapping[str, Any]:
    """locate and parse the config file"""
    try:
        path = os.environ["PYHPCONFIG"]
    except KeyError:
        pass
    else:
        return toml.load(path)
    for path in search_paths:
        try:
            return toml.load(path)
        except FileNotFoundError:
            pass
    raise RuntimeError("failed to locate the config file")
