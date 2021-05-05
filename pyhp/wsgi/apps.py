#!/usr/bin/python3

"""Module containing WSGI apps"""
# The apps modulee is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from abc import ABCMeta, abstractmethod
from typing import Iterable
from . import Environ, StartResponse

__all__ = (
    "WSGIApp",
)


class WSGIApp(metaclass=ABCMeta):
    """abstract base class for wsgi apps"""
    __slots__ = ()

    @abstractmethod
    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterable[bytes]:
        """execute the app"""
        raise NotImplementedError
