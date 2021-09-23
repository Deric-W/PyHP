#!/usr/bin/python3

"""Module containing utilities for WSGI"""
# The utils module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

import sys
from abc import ABCMeta, abstractmethod
from types import TracebackType
from typing import Mapping, Any, TypeVar, Tuple, Optional, Type, TextIO
import toml
from .apps import WSGIApp, SimpleWSGIApp, ConcurrentWSGIApp
from .proxys import LocalStackProxy
from .interfaces import WSGIInterfaceFactory, simple, php
from ..compiler import parsers
from ..compiler.util import Compiler
from ..backends import CodeSourceContainer
from ..backends.util import hierarchy_from_config
from ..backends.caches import CacheSourceContainer


__all__ = (
    "WSGIAppFactory",
    "SimpleWSGIAppFactory",
    "ConcurrentWSGIAppFactory"
)

T = TypeVar("T", bound="WSGIAppFactory")


class WSGIAppFactory(metaclass=ABCMeta):
    """factory for WSGI Apps"""
    __slots__ = ("interface_factory", "compiler", "backend", "cache")

    interface_factory: WSGIInterfaceFactory

    compiler: Compiler

    backend: CodeSourceContainer

    cache: Optional[CacheSourceContainer]

    def __init__(
        self,
        interface_factory: WSGIInterfaceFactory,
        compiler: Compiler,
        backend: CodeSourceContainer,
        cache: Optional[CacheSourceContainer]
    ) -> None:
        self.interface_factory = interface_factory
        self.compiler = compiler
        self.backend = backend
        self.cache = cache

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WSGIAppFactory):
            return self.interface_factory == other.interface_factory \
                and self.compiler == other.compiler \
                and self.backend == other.backend \
                and self.cache == other.cache
        return NotImplemented

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, type: Optional[Type[BaseException]], value: Optional[BaseException], traceback: Optional[TracebackType]) -> bool:  # type: ignore
        self.close()
        return False    # dont swallow exceptions

    @classmethod
    def from_config(cls: Type[T], config: Mapping[str, Any]) -> T:
        """create an instance from config data"""
        compiler = Compiler.from_config(
            parsers.RegexParser.from_config(config.get("parser", {})),
            config.get("compiler", {})
        )
        backend = hierarchy_from_config(compiler, config.get("backend", {}))
        try:
            if isinstance(backend, CacheSourceContainer):   # use the backend if its a cache
                cache = backend  # type: Optional[CacheSourceContainer]
            else:
                cache = None    # else disable it
            return cls(
                cls.get_interface_factory(cache, config.get("interface", {})),
                compiler,
                backend,
                cache
            )
        except BaseException:
            backend.close()
            raise

    @classmethod
    def from_config_file(cls: Type[T], file: TextIO) -> T:
        """create an instance from a config file"""
        return cls.from_config(toml.load(file))

    @staticmethod
    def get_interface_factory(cache: Optional[CacheSourceContainer], interface_config: Mapping[str, Any]) -> WSGIInterfaceFactory:
        """create a interface factory from config data"""
        factory_config = interface_config.get("config", {})
        try:
            interface = interface_config["name"]
        except KeyError:
            return php.PHPWSGIInterfaceFactory.from_config(factory_config, cache)
        if interface == "simple":
            return simple.SimpleWSGIInterfaceFactory.from_config(factory_config, cache)
        elif interface == "php":
            return php.PHPWSGIInterfaceFactory.from_config(factory_config, cache)
        else:
            raise ValueError(f"value {interface} of key 'name' is unknown")

    def detach(self) -> Tuple[CodeSourceContainer, Optional[CacheSourceContainer]]:
        """detach the app from the backend and the cache without closing them"""
        return self.backend, self.cache

    def close(self) -> None:
        """close the backend and cache"""
        backend, cache = self.detach()
        try:
            if cache is not None and backend is not cache:    # cache and backend can be identical
                cache.close()
        finally:    # dont stop on error
            backend.close()

    @abstractmethod
    def app(self, code_name: str) -> WSGIApp:
        """create a new WSGI app executing the code represented by code_name from the backend"""
        raise NotImplementedError


class SimpleWSGIAppFactory(WSGIAppFactory):
    """factory for SimpleWSGIApps"""
    __slots__ = ()

    def app(self, code_name: str) -> SimpleWSGIApp:
        """create a new SimpleWSGIApp executing the code represented by code_name from the backend"""
        return SimpleWSGIApp(
            self.backend[code_name],
            self.interface_factory
        )


class ConcurrentWSGIAppFactory(WSGIAppFactory):
    """factory for ConcurrentWSGIApps"""
    __slots__ = ("proxy", "old_stdout")

    proxy: LocalStackProxy[TextIO]

    old_stdout: TextIO

    def __init__(
        self,
        interface_factory: WSGIInterfaceFactory,
        compiler: Compiler,
        backend: CodeSourceContainer,
        cache: Optional[CacheSourceContainer]
    ) -> None:
        self.interface_factory = interface_factory
        self.compiler = compiler
        self.backend = backend
        self.cache = cache
        self.old_stdout = sys.stdout
        self.proxy = LocalStackProxy(self.old_stdout)
        sys.stdout = self.proxy     # type: ignore

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ConcurrentWSGIAppFactory):
            return self.interface_factory == other.interface_factory \
                and self.compiler == other.compiler \
                and self.backend == other.backend \
                and self.cache == other.cache \
                and self.proxy == other.proxy
        return NotImplemented

    def app(self, code_name: str) -> WSGIApp:
        """create a new ConcurrentWSGIApp executing the code represented by code_name from the backend"""
        return ConcurrentWSGIApp(
            code_name,
            self.backend,
            self.proxy,     # type: ignore
            self.interface_factory
        )

    def close(self) -> None:
        """close the backend and cache and reset sys.stdout"""
        backend, cache = self.detach()
        try:
            try:
                if cache is not None and backend is not cache:    # cache and backend can be identical
                    cache.close()
            finally:    # dont stop on error
                backend.close()
        finally:    # dont stop on error too
            sys.stdout = self.old_stdout
