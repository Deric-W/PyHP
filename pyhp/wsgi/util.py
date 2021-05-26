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

import re
import sys
from abc import ABCMeta, abstractmethod
from types import TracebackType
from typing import Mapping, Any, TypeVar, Tuple, Optional, Type, TextIO
import toml
from .apps import WSGIApp, SimpleWSGIApp, ConcurrentWSGIApp
from .proxys import LocalStackProxy
from .interfaces import WSGIInterfaceFactory, simple, php
from ..compiler import Parser, CodeBuilder, generic, parsers
from ..compiler.util import Compiler, Dedenter
from ..backends import CodeSourceContainer, util
from ..backends.caches import CacheSourceContainer


__all__ = (
    "create_backend",
    "create_compiler",
    "WSGIAppFactory",
    "SimpleWSGIAppFactory",
    "ConcurrentWSGIAppFactory"
)

T = TypeVar("T", bound="WSGIAppFactory")


def create_backend(compiler: Compiler[Parser, CodeBuilder], backend_config: Mapping[str, Any]) -> CodeSourceContainer:
    """create a backend from config data"""
    try:
        resolve = backend_config["resolve"]
    except KeyError:
        hierarchy_builder = util.ModuleHierarchyBuilder(compiler)  # type: util.ConfigHierarchyBuilder
    else:
        if resolve == "module":
            hierarchy_builder = util.ModuleHierarchyBuilder(compiler)
        elif resolve == "path":
            hierarchy_builder = util.PathHierarchyBuilder(compiler)
        else:
            raise ValueError(f"value '{resolve}' of key 'resolve' is unknown")
    try:
        hierarchy_builder.add_config(backend_config["containers"])
    except BaseException:   # close already constructed containers
        try:
            hierarchy = hierarchy_builder.hierarchy()
        except IndexError:  # no containers constructed, ignore
            pass
        else:
            hierarchy.close()
        raise   # dont hide the error
    return hierarchy_builder.hierarchy()


def create_compiler(parser: Parser, compiler_config: Mapping[str, Any]) -> Compiler[Parser, CodeBuilder]:
    """create a compiler from config data"""
    try:
        optimization_level = compiler_config["optimization_level"]
    except KeyError:
        optimization_level = -1
    else:
        if not isinstance(optimization_level, int):
            raise ValueError("value of key 'optimization_level' expected to be an int")
    builder = generic.GenericCodeBuilder(optimization_level)    # type: CodeBuilder
    if compiler_config.get("dedent", True):
        builder = Dedenter(builder)
    return Compiler(parser, builder)


class WSGIAppFactory(metaclass=ABCMeta):
    """factory for WSGI Apps"""
    __slots__ = ("interface_factory", "compiler", "backend", "cache")

    interface_factory: WSGIInterfaceFactory

    compiler: Compiler[Parser, CodeBuilder]

    backend: CodeSourceContainer

    cache: Optional[CacheSourceContainer]

    def __init__(
        self,
        interface_factory: WSGIInterfaceFactory,
        compiler: Compiler[Parser, CodeBuilder],
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
        compiler = cls.get_compiler(
            cls.get_parser(config.get("parser", {})),
            config.get("compiler", {})
        )
        backend_config = config.get("backend", {})
        backend = cls.get_backend(compiler, backend_config)
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
    def get_parser(parser_config: Mapping[str, Any]) -> Parser:
        """create a parser from config data"""
        return parsers.RegexParser(
            re.compile(parser_config.get("start", r"<\?pyhp\s")),
            re.compile(parser_config.get("end", r"\s\?>"))
        )

    @staticmethod
    def get_compiler(parser: Parser, compiler_config: Mapping[str, Any]) -> Compiler[Parser, CodeBuilder]:
        """create a compiler from config data"""
        return create_compiler(parser, compiler_config)

    @staticmethod
    def get_backend(compiler: Compiler[Parser, CodeBuilder], backend_config: Mapping[str, Any]) -> CodeSourceContainer:
        """create a backend from config data"""
        return create_backend(compiler, backend_config)

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
        compiler: Compiler[Parser, CodeBuilder],
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
