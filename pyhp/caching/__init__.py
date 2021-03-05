#!/usr/bin/python3

"""Package containing the caching subsystem"""
# The caching package is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from types import TracebackType
from typing import (
    Generic,
    TypeVar,
    NamedTuple,
    Type,
    Mapping,
    ValuesView,
    ItemsView,
    Any,
    Union,
    Optional,
    Iterator,
    Pattern,
    Tuple
)
from ..compiler import Code
from ..compiler.util import Compiler


__all__ = (
    "SourceInfo",
    "CodeSource",
    "DirectCodeSource",
    "TimestampedCodeSource",
    "CodeSourceDecorator",
    "CacheSource",
    "ContainerValuesView",
    "ContainerItemsView",
    "CodeSourceContainer",
    "CodeSourceContainerDecorator",
    "CacheSourceContainer",
    "memory",
    "files",
    "zipfiles",
    "util"
)


S = TypeVar("S", bound="CodeSource")
T = TypeVar("T", bound="TimestampedCodeSource")
CS = TypeVar("CS", bound="CacheSource")

C = TypeVar("C", bound="CodeSourceContainer")


class SourceInfo(NamedTuple):
    """named tuple containing all timestamps of a source"""
    mtime: int
    ctime: int
    atime: int


class CacheException(Exception):
    """Exception raised by cache operations"""


class NotCachedException(CacheException):
    """Exception raised by clearing sources currently not in the cache"""


class CodeSource(metaclass=ABCMeta):
    """abc for representing a code object inside a storage"""
    __slots__ = ("__weakref__",)

    def __enter__(self: S) -> S:
        return self

    def __exit__(self, type: Optional[Type[BaseException]], value: Optional[BaseException], traceback: Optional[TracebackType]) -> Optional[bool]:  # type: ignore
        self.close()
        return False    # dont swallow exceptions

    @abstractmethod
    def code(self) -> Code:
        """retrieve the represented code object"""
        raise NotImplementedError

    def close(self) -> None:
        """perform cleanup actions"""
        pass    # may be changed in subclasses


class DirectCodeSource(CodeSource):
    """abc for code sources with source code access"""
    __slots__ = ()

    @abstractmethod
    def source(self) -> str:
        """retrieve the source code"""
        raise NotImplementedError

    def size(self) -> int:
        """retrieve the size of the source code"""
        return len(self.source())


class TimestampedCodeSource(CodeSource):
    """abc for code sources with timestamps"""
    __slots__ = ()

    def info(self) -> SourceInfo:
        """retrieve all timestamps"""
        return SourceInfo(
            self.mtime(),
            self.ctime(),
            self.atime()
        )

    @abstractmethod
    def mtime(self) -> int:
        """retrieve the modification timestamp in ns"""
        raise NotImplementedError

    @abstractmethod
    def ctime(self) -> int:
        """retrieve the creation timestamp in ns"""
        raise NotImplementedError

    @abstractmethod
    def atime(self) -> int:
        """retireve the access timestamp in ns"""
        raise NotImplementedError


class CodeSourceDecorator(Generic[S], CodeSource):
    """abc for code source decorators"""
    __slots__ = ("code_source",)

    code_source: S

    def code(self) -> Code:
        """delegate call to decorated code source"""
        return self.code_source.code()

    def detach(self) -> S:
        """return the decorated code source, leaving the decorator in an undefined state"""
        return self.code_source

    def close(self) -> None:
        """perform cleanup actions and close the decorated code source"""
        self.detach().close()


class CacheSource(CodeSourceDecorator[S]):
    """abc for code sources with caching features"""
    __slots__ = ()

    def fetch(self) -> None:
        """load the represented code object in the cache"""
        self.code()     # may be replaced by a more specific implementation

    def gc(self) -> bool:
        """remove the represented code object from the cache if it is no longer valid"""
        if self.cached():   # may be replaced by a specific thread safe implementation
            return False
        try:
            self.clear()
        except NotCachedException:
            return False
        return True

    @abstractmethod
    def clear(self) -> None:
        """remove the represented code object from the cache"""
        raise NotImplementedError

    @abstractmethod
    def cached(self) -> bool:
        """check if the represented code object is in the cache and valid"""
        raise NotImplementedError


class ContainerValuesView(ValuesView[S]):
    """ValuesView for Mappings of context managers"""
    __slots__ = ()

    _mapping: Mapping[str, S]

    def __contains__(self, value: object) -> bool:
        """custom contains implementation which closes the retrieved source"""
        for key in self._mapping:
            with self._mapping[key] as source:
                if source is value or source == value:
                    return True
        return False


class ContainerItemsView(ItemsView[str, S]):
    """ItemsView for Mapping of context managers"""
    __slots__ = ()

    _mapping: Mapping[str, S]

    def __contains__(self, item: object) -> bool:
        """custom contains implementation which closes the retrieved source"""
        key: object
        value: object
        key, value = item   # type: ignore
        if isinstance(key, str):
            try:
                source = self._mapping[key]
            except KeyError:
                return False
            with source:
                return source is value or source == value
        raise TypeError(f"first value is expected to be a str, not '{type(key)}'")


class CodeSourceContainer(Mapping[str, S]):
    """abc for representing a storage of code sources"""
    __slots__ = ("__weakref__",)

    def __enter__(self: C) -> C:
        return self

    def __exit__(self, type: Optional[Type[BaseException]], value: Optional[BaseException], traceback: Optional[TracebackType]) -> Optional[bool]:  # type: ignore
        self.close()
        return False    # dont swallow exceptions

    def __contains__(self, name: object) -> bool:
        """custom contains implementation which closes the retrieved source"""
        if isinstance(name, str):
            try:
                source = self[name]
            except KeyError:
                return False
            source.close()
            return True
        raise TypeError(f"name is expected to be a str, not '{type(name)}'")

    @classmethod
    @abstractmethod
    def from_config(cls, config: Mapping[str, Any], before: Union[Compiler, CodeSourceContainer]) -> CodeSourceContainer[S]:
        """create a instance from configuration data"""
        raise NotImplementedError

    def values(self) -> ValuesView[S]:
        """custom ValueView which closes retrieved sources"""
        return ContainerValuesView(self)

    def items(self) -> ItemsView[str, S]:
        """custom ItemsView which closes retrieved sources"""
        return ContainerItemsView(self)

    def search(self, pattern: Pattern[str]) -> Iterator[Tuple[str, S]]:
        """yield all sources with names which match the pattern"""
        for name in self.keys():
            if pattern.match(name) is not None:
                yield name, self[name]

    def close(self) -> None:
        """perform cleanup actions"""
        pass


class TimestampedCodeSourceContainer(CodeSourceContainer[T]):
    """abc for containers of TimestampedCodeSources"""
    __slots__ = ()

    # these methods allow for performance optimizations
    def mtime(self, name: str) -> int:
        """retrieve the modification timestamp of name"""
        with self[name] as source:
            return source.mtime()

    def ctime(self, name: str) -> int:
        """retrieve the creation timestamp of name"""
        with self[name] as source:
            return source.ctime()

    def atime(self, name: str) -> int:
        """retrieve the access timestamp of name"""
        with self[name] as source:
            return source.atime()

    def info(self, name: str) -> SourceInfo:
        """retireve the info about name"""
        with self[name] as source:
            return source.info()


class CodeSourceContainerDecorator(CodeSourceContainer[S], Generic[C, S]):
    """abc code source container decorators"""
    __slots__ = ("source_container",)

    source_container: C

    def __getitem__(self, name: str) -> S:
        """delegate to decorated container"""
        return self.source_container[name]

    def __iter__(self) -> Iterator[str]:
        """delegate to decorated container"""
        return iter(self.source_container)

    def __len__(self) -> int:
        """delegate to decorated container"""
        return len(self.source_container)

    def __contains__(self, name: object) -> bool:
        """delegate to decorated container"""
        return name in self.source_container

    def detach(self) -> C:
        """return the decorated code source container, leaving the decorator in an undefined state"""
        return self.source_container

    def close(self) -> None:
        """detach and close decorated code source container"""
        self.detach().close()


class CacheSourceContainer(CodeSourceContainerDecorator[C, CS]):
    """abc for containers of cache sources"""
    __slots__ = ()

    @abstractmethod
    def cached(self) -> Mapping[str, CS]:
        """return a mapping of cached sources"""
        raise NotImplementedError

    def gc(self) -> int:
        """garbage collect all cached sources and return the number removed"""
        number = 0
        for source in self.values():    # may be replaced by a specific thread safe implementation
            if source.gc():
                number += 1
        return number

    def clear(self) -> None:
        """remove all sources from the cache"""
        for source in self.cached().values():    # may be replaced by a specific thread safe implementation
            try:
                source.clear()
            except NotCachedException:  # already removed
                pass
