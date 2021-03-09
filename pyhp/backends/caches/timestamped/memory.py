#!/usr/bin/python3

"""Package containing memory implementations of timestamp-based caches"""
# The caching package is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only


from __future__ import annotations
import time
from typing import TypeVar, Mapping, Any, Dict, Tuple
from . import check_mtime
from .. import (
    CacheSource,
    CacheSourceContainer,
    NotCachedException
)
from ... import (
    ConfigHierarchy,
    TimestampedCodeSource,
    TimestampedCodeSourceContainer
)
from ....compiler import Code


__all__ = (
    "MemoryCacheSource",
    "UnboundedMemoryCache"
)

S = TypeVar("S", bound=TimestampedCodeSource)


class MemoryCacheSource(CacheSource[S]):
    """in-memory cache source"""
    __slots__ = ("name", "storage", "ttl")

    name: str

    storage: Dict[str, Tuple[Code, int]]

    ttl: int

    def __init__(self, code_source: S, name: str, storage: Dict[str, Tuple[Code, int]], ttl: int = 0) -> None:
        self.code_source = code_source
        self.name = name
        self.storage = storage
        self.ttl = ttl

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MemoryCacheSource):
            return self.code_source == other.code_source \
                and self.name == other.name \
                and self.storage is other.storage \
                and self.ttl == other.ttl
        return NotImplemented

    def code(self) -> Code:
        """retrieve the represented code object"""
        try:
            code, timestamp = self.storage[self.name]
        except KeyError:    # not cached
            code = self.code_source.code()
            self.storage[self.name] = (code, time.time_ns())
            return code
        if check_mtime(self.code_source.mtime(), timestamp, self.ttl):
            return code
        code = self.code_source.code()  # outdated
        self.storage[self.name] = (code, time.time_ns())
        return code

    def cached(self) -> bool:
        """check if the represented code object is in the cache and valid"""
        try:
            _, timestamp = self.storage[self.name]
        except KeyError:
            return False    # not cached
        return check_mtime(self.code_source.mtime(), timestamp, self.ttl)

    def clear(self) -> None:
        """remove the represented code object from the cache"""
        try:
            del self.storage[self.name]
        except KeyError as e:
            raise NotCachedException("cache already clear") from e


class UnboundedMemoryCache(CacheSourceContainer[TimestampedCodeSourceContainer[S], MemoryCacheSource[S]]):
    """in-memory cache without a size limit"""
    __slots__ = ("storage", "ttl")

    storage: Dict[str, Tuple[Code, int]]

    ttl: int

    def __init__(self, source_container: TimestampedCodeSourceContainer[S], ttl: int = 0) -> None:
        self.source_container = source_container
        self.storage = {}
        self.ttl = ttl

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnboundedMemoryCache):
            return self.source_container == other.source_container \
                and self.storage == other.storage \
                and self.ttl == other.ttl
        return NotImplemented

    def __getitem__(self, name: str) -> MemoryCacheSource[S]:
        return MemoryCacheSource(
            self.source_container[name],
            name,
            self.storage,
            self.ttl
        )

    @classmethod
    def from_config(cls, config: Mapping[str, Any], before: ConfigHierarchy) -> UnboundedMemoryCache:
        """create a instance from configuration data"""
        if isinstance(before, TimestampedCodeSourceContainer):
            ttl = config.get("ttl", 0)
            if isinstance(ttl, (int, float)):
                return cls(before, int(ttl * 1e9))  # convert from s to ns
            raise ValueError("expected value of key 'ttl' to be a int or float")
        raise ValueError(f"{cls.__name__} has to decorate another TimestampedCodeSourceContainer")

    def gc(self) -> int:
        """garbage collect all cached sources and return the number removed"""
        removed = 0
        for name in tuple(self.storage):    # dict does not like being modified while iterating
            timestamp = self.storage[name][1]
            if not check_mtime(self.source_container.mtime(name), timestamp, self.ttl):
                try:
                    del self.storage[name]
                except KeyError:    # entry already removed
                    pass
                removed += 1
        return removed

    def clear(self) -> None:
        """remove all sources from the cache"""
        self.storage.clear()
