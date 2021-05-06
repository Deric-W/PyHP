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
from contextlib import redirect_stdout
from io import StringIO
from types import TracebackType
from typing import Iterable, ContextManager, TypeVar, Optional, Type
from . import Environ, StartResponse
from .interfaces import WSGIInterfaceFactory
from ..backends import CodeSource

__all__ = (
    "WSGIApp",
    "SimpleWSGIApp"
)

T = TypeVar("T")


class WSGIApp(metaclass=ABCMeta):
    """abstract base class for wsgi apps who capture output"""
    __slots__ = ("interface_factory", "__weakref__")

    interface_factory: WSGIInterfaceFactory

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, type: Optional[Type[BaseException]], value: Optional[BaseException], traceback: Optional[TracebackType]) -> bool:    # type: ignore
        self.close()
        return False

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WSGIApp):
            return self.interface_factory == other.interface_factory \
                and self.code_source() == other.code_source()
        return NotImplemented

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterable[bytes]:
        """execute the app"""
        stopped = False     # dont yield if Generator.close() was called
        code = self.code_source().code()
        interface = self.interface_factory.interface(environ, start_response)
        try:
            iterator = code.execute({"PyHP": interface})
            try:                    # call .end_headers() for yielding the first time
                with self.redirect_stdout(StringIO()) as buffer:
                    text = next(iterator)
            except StopIteration:   # there was only a code section, yield its output
                interface.end_headers()
                yield buffer.getvalue().encode("utf8")
                return
            # there are more sections, continue
            interface.end_headers()
            yield buffer.getvalue().encode("utf8")
            yield text.encode("utf8")
            while True:
                try:
                    with self.redirect_stdout(StringIO()) as buffer:
                        text = next(iterator)
                except StopIteration:
                    yield buffer.getvalue().encode("utf8")
                    break
                yield buffer.getvalue().encode("utf8")
                yield text.encode("utf8")
        except GeneratorExit:
            stopped = True
        finally:                # interface.close may produce output
            with self.redirect_stdout(StringIO()) as buffer:
                interface.close()
            if not stopped:
                yield buffer.getvalue().encode("utf8")  # .end_headers() has already been called

    @abstractmethod
    def redirect_stdout(self, buffer: StringIO) -> ContextManager[StringIO]:
        """redirect stdout to a buffer and return a context manager"""
        raise NotImplementedError

    @abstractmethod
    def code_source(self) -> CodeSource:
        """return a code source which will not be closed"""
        raise NotImplementedError

    def close(self) -> None:
        """perform cleanup actions"""
        pass


class SimpleWSGIApp(WSGIApp):
    """implementation for single threaded environments"""
    __slots__ = ("source")

    source: CodeSource

    def __init__(self, code_source: CodeSource, interface_factory: WSGIInterfaceFactory) -> None:
        self.source = code_source
        self.interface_factory = interface_factory

    def redirect_stdout(self, buffer: StringIO) -> ContextManager[StringIO]:
        """redirect stdout to a buffer and return a context manager"""
        return redirect_stdout(buffer)

    def code_source(self) -> CodeSource:
        """return a code source"""
        return self.source

    def close(self) -> None:
        """close the code source"""
        self.source.close()
