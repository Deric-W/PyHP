#!/usr/bin/python3

"""Package containing caches to decorate backends"""
# The backends.caches package is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only


from __future__ import annotations
from abc import abstractmethod
from typing import (
    TypeVar,
    Mapping,
    Iterator,
    Tuple,
    Any,
    ValuesView,
    ItemsView
)
from .. import (
    CodeSource,
    CodeSourceDecorator,
    CodeSourceContainer,
    CodeSourceContainerDecorator,
    ClosingValuesView,
    ClosingItemsView
)


__all__ = (
    "CacheException",
    "CacheSource",
    "CacheSourceContainer",
    "ClosingValuesView",
    "ClosingItemsView",
    "CachedMapping",
    "timestamped"
)

S = TypeVar("S", bound=CodeSource)
C = TypeVar("C", bound=CodeSourceContainer)
CS = TypeVar("CS", bound="CacheSource")


class CacheException(Exception):
    """Exception raised by cache operations"""


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
        return self.clear()

    @abstractmethod
    def clear(self) -> bool:
        """remove the represented code object from the cache and return if it was cached"""
        raise NotImplementedError

    @abstractmethod
    def cached(self) -> bool:
        """check if the represented code object is in the cache and valid"""
        raise NotImplementedError


class CacheSourceContainer(CodeSourceContainerDecorator[C, CS]):
    """abc for containers of cache sources"""
    __slots__ = ()

    def cached(self) -> Mapping[str, CS]:
        """return a mapping of cached sources"""
        return CachedMapping(self)

    def gc(self) -> int:
        """garbage collect all cached sources and return the number removed"""
        number = 0
        for source in self.values():    # may be replaced by a specific thread safe implementation
            try:
                if source.gc():
                    number += 1
            finally:
                source.close()
        return number

    def clear(self) -> None:
        """remove all sources from the cache"""
        for source in self.cached().values():    # may be replaced by a specific thread safe implementation
            try:
                source.clear()
            finally:
                source.close()


class CachedValuesView(ClosingValuesView[CS]):
    """ValuesView for CachedMapping"""
    __slots__ = ()

    _mapping: CachedMapping[CS]

    def __iter__(self) -> Iterator[CS]:
        """optimized version of ValuesView.__iter__"""
        for source in self._mapping.container.values():
            try:
                cached = source.cached()
            except Exception:
                source.close()
                raise
            if cached:
                yield source
            else:
                source.close()


class CachedItemsView(ClosingItemsView[CS]):
    """ItemsView for CachedMapping"""
    __slots__ = ()

    _mapping: CachedMapping[CS]

    def __iter__(self) -> Iterator[Tuple[str, CS]]:
        """optimized version of ItemsView.__iter__"""
        for name, source in self._mapping.container.items():
            try:
                cached = source.cached()
            except Exception:
                source.close()
                raise
            if cached:
                yield (name, source)
            else:
                source.close()


class CachedMapping(Mapping[str, CS]):
    """Mapping of cache sources currently cached"""
    __slots__ = ("container",)

    container: CacheSourceContainer[Any, CS]

    def __init__(self, container: CacheSourceContainer[Any, CS]) -> None:
        self.container = container

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CachedMapping):
            return self.container == other.container
        return NotImplemented

    def __getitem__(self, name: str) -> CS:
        source = self.container[name]
        try:
            cached = source.cached()
        except Exception:
            source.close()
            raise
        if cached:
            return source
        source.close()
        raise KeyError(f"source for '{name}' exists but is not cached")

    def __iter__(self) -> Iterator[str]:
        for name, source in self.container.items():
            try:
                if source.cached():
                    yield name
            finally:
                source.close()

    def __len__(self) -> int:
        x = 0
        for _ in self:
            x += 1
        return x

    def __contains__(self, name: object) -> bool:
        if isinstance(name, str):
            try:
                source = self.container[name]
            except KeyError:
                return False
            with source:
                return source.cached()
        return False

    def values(self) -> ValuesView[CS]:
        """custom ClosingValuesView with optimizations"""
        return CachedValuesView(self)

    def items(self) -> ItemsView[str, CS]:
        """custom ClosingItemsView with optimizations"""
        return CachedItemsView(self)
