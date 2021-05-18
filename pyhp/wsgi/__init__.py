#!/usr/bin/python3

"""Package containing the wsgi subsystem"""
# The wsgi package is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from typing import Any, Optional, Tuple, Type, Callable, List, Dict, TypeVar, Iterable
from types import TracebackType

__all__ = (
    "ExcInfo",
    "StartResponse",
    "Environ",
    "map_failsafe",
    "apps",
    "interfaces",
    "util",
    "proxys"
)

# WSGI types
ExcInfo = Tuple[Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]]

StartResponse = Callable[[str, List[Tuple[str, str]], Optional[ExcInfo]], Callable[[bytes], None]]

Environ = Dict[str, Any]

T = TypeVar("T")


def map_failsafe(function: Callable[[T], None], iterator: Iterable[T]) -> None:
    """apply a function to all elements of an iterable, not stopping on error"""
    previous_exception = None
    for obj in iterator:
        try:
            function(obj)
        except Exception as e:  # dont stop when function fails
            e.__context__ = previous_exception
            previous_exception = e
    if previous_exception is not None:  # dont swallow errors
        raise previous_exception
