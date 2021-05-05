#!/usr/bin/python3

"""Package containing the wsgi interfaces"""
# The interfaces package is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from abc import ABCMeta, abstractmethod
from types import TracebackType
from typing import Any, Optional, Type, TypeVar, Mapping
from .. import Environ, StartResponse
from ...backends.caches import CacheSourceContainer


__all__ = (
    "WSGIInterface",
    "WSGIInterfaceFactory"
)

T = TypeVar("T")


class WSGIInterface(metaclass=ABCMeta):
    """base class for all Interfaces"""
    __slots__ = ("environ", "start_response")

    environ: Environ

    start_response: StartResponse

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WSGIInterface):
            return self.environ == other.environ \
                and self.start_response == other.start_response     # type: ignore
        return NotImplemented

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, type: Optional[Type[BaseException]], value: Optional[BaseException], tracbeack: Optional[TracebackType]) -> bool:    # type: ignore
        self.close()
        return False    # dont swallow exceptions

    @abstractmethod
    def end_headers(self) -> None:
        """prepare for output by calling start_response"""
        raise NotImplementedError

    def close(self) -> None:
        """do cleanup actions"""
        pass


class WSGIInterfaceFactory(metaclass=ABCMeta):
    """base class for interface factories"""
    __slots__ = ()

    @abstractmethod
    @classmethod
    def from_config(cls: Type[T], config: Mapping[str, Any], cache: CacheSourceContainer) -> T:
        """create an instance from config data and a cache"""
        raise NotImplementedError

    @abstractmethod
    def interface(self, environ: Environ, start_response: StartResponse) -> WSGIInterface:
        """create an interface"""
        raise NotImplementedError
