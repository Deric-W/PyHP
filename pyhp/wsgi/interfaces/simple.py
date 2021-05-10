#!/usr/bin/python3

"""Module containing a simple interface"""
# The simple module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
from wsgiref.headers import Headers
from http import HTTPStatus
from typing import Type, Mapping, Any, List, Tuple
from . import WSGIInterface, WSGIInterfaceFactory
from .. import Environ, StartResponse
from ...backends.caches import CacheSourceContainer

__all__ = (
    "SimpleWSGIInterface",
    "SimpleWSGIInterfaceFactory"
)

# the many type: ignore comments are caused by https://github.com/python/mypy/issues/5485


class SimpleWSGIInterface(WSGIInterface):
    """simple interface implementation"""
    __slots__ = ("status", "headers", "cache")

    status: str

    headers: Headers

    cache: CacheSourceContainer

    def __init__(self, environ: Environ, start_response: StartResponse, status: str, headers: Headers, cache: CacheSourceContainer) -> None:
        self.environ = environ
        self.start_response = start_response    # type: ignore
        self.status = status
        self.headers = headers
        self.cache = cache

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SimpleWSGIInterface):
            return all((    # continuations would disallow the type: ignore comment
                self.environ == other.environ,
                self.start_response == other.start_response,    # type: ignore
                self.status == other.status,
                self.headers == other.headers,
                self.cache == other.cache
            ))
        elif isinstance(other, WSGIInterface):
            return self.environ == other.environ \
                and self.start_response == other.start_response     # type: ignore
        return NotImplemented

    def end_headers(self) -> None:
        """call start_response with the current headers"""
        self.start_response(self.status, self.headers.items())  # type: ignore

    def set_status_code(self, code: int) -> None:
        """change self.status to the specified status code"""
        self.status = f"{code} {HTTPStatus(code).phrase}"

    def get_status_code(self) -> int:
        """return the current status code"""
        return int(self.status.partition(" ")[0])


class SimpleWSGIInterfaceFactory(WSGIInterfaceFactory):
    """factory for simple interfaces"""
    __slots__ = ("default_status", "default_headers", "cache")

    default_status: str

    default_headers: List[Tuple[str, str]]

    cache: CacheSourceContainer     # may be used by multiple factories, do not close

    def __init__(self, default_status: str, default_headers: List[Tuple[str, str]], cache: CacheSourceContainer) -> None:
        self.default_status = default_status
        self.default_headers = default_headers
        self.cache = cache

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SimpleWSGIInterfaceFactory):
            return self.default_status == other.default_status \
                and self.default_headers == other.default_headers \
                and self.cache == other.cache
        return NotImplemented

    @classmethod
    def from_config(cls: Type[SimpleWSGIInterfaceFactory], config: Mapping[str, Any], cache: CacheSourceContainer) -> SimpleWSGIInterfaceFactory:
        """create an instance from config data and a cache"""
        try:
            status = config["default_status"]
            if not isinstance(status, str):
                raise ValueError("value of key 'default_status' expected to be a str")
        except KeyError:
            status = "200 OK"
        try:
            headers = config["default_headers"]
            if not isinstance(headers, list):
                raise ValueError("value of key 'default_headers' expected to be a list")
        except KeyError:
            headers = [("Content-Type", 'text/html; charset="UTF-8"')]
        return cls(status, headers, cache)

    def interface(self, environ: Environ, start_response: StartResponse) -> SimpleWSGIInterface:
        """create a new simple wsgi interface"""
        return SimpleWSGIInterface(
            environ,
            start_response,
            self.default_status,
            Headers(self.default_headers.copy()),
            self.cache
        )
