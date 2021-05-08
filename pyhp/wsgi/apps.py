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
from typing import Iterable, Iterator, ContextManager, TypeVar, Optional, Type, Generator
from . import Environ, StartResponse
from .interfaces import WSGIInterfaceFactory, WSGIInterface
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
        code = self.code_source().code()
        buffer = StringIO()
        interface = self.interface_factory.interface(environ, start_response)
        try:
            iterator = code.execute({"PyHP": interface})
            with self.redirect_stdout(buffer):
                buffer.write(next(iterator))
        except (StopIteration, SystemExit):   # no more sections, return
            yield from self.stop_request(interface, buffer)
            return
        except BaseException:   # an error happend, reraise
            yield from self.stop_request(interface, buffer)
            raise
        # send headers and continue
        try:
            interface.end_headers()
        except BaseException:
            with self.redirect_stdout(buffer):
                interface.close()
            raise
        yield from self.finish_request(interface, iterator, buffer)

    def finish_request(self, interface: WSGIInterface, iterator: Iterator[str], buffer: StringIO) -> Generator[bytes, None, None]:
        """finish a request with headers already sent"""
        stopped = False     # dont yield if Generator.close() was called
        try:
            yield buffer.getvalue().encode("utf8")
            while True:
                buffer = StringIO()
                try:
                    with self.redirect_stdout(buffer) as buffer:
                        buffer.write(next(iterator))
                except (StopIteration, SystemExit):     # no more sections, return
                    yield buffer.getvalue().encode("utf8")
                    break
                yield buffer.getvalue().encode("utf8")
        except GeneratorExit:
            stopped = True
        finally:    # .end_headers has already been called
            with self.redirect_stdout(StringIO()) as buffer:
                interface.close()
            if not stopped:
                yield buffer.getvalue().encode("utf8")

    def stop_request(self, interface: WSGIInterface, buffer: StringIO) -> Generator[bytes, None, None]:
        """stop a request with no headers already sent"""
        try:
            interface.end_headers()
        except BaseException:   # error, can not send output
            with self.redirect_stdout(buffer):
                interface.close()
            raise
        # success, can send output
        try:
            with self.redirect_stdout(buffer):
                interface.close()
        finally:    # safe because we dont yield in the try block
            yield buffer.getvalue().encode("utf8")

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
    __slots__ = ("source",)

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
