#!/usr/bin/python3

"""Package containing memory implementations of timestamp-based caches"""
# The backends.caches.timestamped.memory module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only


from __future__ import annotations
import time
from abc import abstractmethod
from threading import Lock
from typing import (
    TypeVar,
    Mapping,
    Any,
    Dict,
    Tuple,
    MutableMapping,
    OrderedDict,
    Iterator,
    KeysView,
    ValuesView,
    ItemsView,
    overload,
    Union
)
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
    "CacheEntry",
    "MemoryCacheSource",
    "MemoryCache",
    "MemoryCacheStrategy",
    "UnboundedCacheStrategy",
    "LRUCacheStrategy"
)

S = TypeVar("S", bound=TimestampedCodeSource)
K = TypeVar("K")
V = TypeVar("V")
T = TypeVar("T")

POP_SENTINEL: object = object()

CacheEntry = Tuple[Code, int]


class MemoryCacheSource(CacheSource[S]):
    """in-memory cache source"""
    __slots__ = ("name", "strategy", "ttl")

    name: str

    strategy: MemoryCacheStrategy[str, CacheEntry]

    ttl: int

    def __init__(self, code_source: S, name: str, strategy: MemoryCacheStrategy[str, CacheEntry], ttl: int = 0) -> None:
        self.code_source = code_source
        self.name = name
        self.strategy = strategy
        self.ttl = ttl

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MemoryCacheSource):
            return self.code_source == other.code_source \
                and self.name == other.name \
                and self.strategy == other.strategy \
                and self.ttl == other.ttl
        return NotImplemented

    def code(self) -> Code:
        """retrieve the represented code object"""
        try:
            code, timestamp = self.strategy[self.name]
        except KeyError:    # not cached
            code = self.code_source.code()
            self.strategy[self.name] = (code, time.time_ns())
            return code
        if check_mtime(self.code_source.mtime(), timestamp, self.ttl):
            return code
        code = self.code_source.code()  # outdated
        self.strategy[self.name] = (code, time.time_ns())
        return code

    def cached(self) -> bool:
        """check if the represented code object is in the cache and valid"""
        try:
            _, timestamp = self.strategy.peek(self.name)
        except KeyError:
            return False    # not cached
        return check_mtime(self.code_source.mtime(), timestamp, self.ttl)

    def clear(self) -> None:
        """remove the represented code object from the cache"""
        try:
            del self.strategy[self.name]
        except KeyError as e:
            raise NotCachedException("cache already clear") from e


class MemoryCache(CacheSourceContainer[TimestampedCodeSourceContainer[S], MemoryCacheSource[S]]):
    """in-memory cache with different strategies"""
    __slots__ = ("strategy", "ttl")

    strategy: MemoryCacheStrategy[str, CacheEntry]

    ttl: int

    def __init__(self, source_container: TimestampedCodeSourceContainer[S], strategy: MemoryCacheStrategy[str, CacheEntry], ttl: int = 0) -> None:
        self.source_container = source_container
        self.strategy = strategy
        self.ttl = ttl

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MemoryCache):
            return self.source_container == other.source_container \
                and self.strategy == other.strategy \
                and self.ttl == other.ttl
        return NotImplemented

    def __getitem__(self, name: str) -> MemoryCacheSource[S]:
        return MemoryCacheSource(
            self.source_container[name],
            name,
            self.strategy,
            self.ttl
        )

    @classmethod
    def from_config(cls, config: Mapping[str, Any], before: ConfigHierarchy) -> MemoryCache:
        """create a instance from configuration data"""
        if isinstance(before, TimestampedCodeSourceContainer):
            ttl = config.get("ttl", 0)
            if isinstance(ttl, (int, float)):
                strategy = config.get("strategy", "unbounded")
                if strategy == "unbounded":
                    strategy_obj = UnboundedCacheStrategy()  # type: MemoryCacheStrategy
                elif strategy == "lru":
                    max_entries = config["max_entries"]
                    if isinstance(max_entries, int):
                        strategy_obj = LRUCacheStrategy(max_entries)
                    else:
                        raise ValueError("expected value of key 'max_entries' to be a int")
                else:
                    raise ValueError(f"cache strategy '{strategy}' unknown")
                return cls(before, strategy_obj, int(ttl * 1e9))  # convert from s to ns
            raise ValueError("expected value of key 'ttl' to be a int or float")
        raise ValueError(f"{cls.__name__} has to decorate another TimestampedCodeSourceContainer")

    def gc(self) -> int:
        """garbage collect all cached sources and return the number removed"""
        removed = 0
        for name in tuple(self.strategy):    # dict does not like being modified while iterating
            timestamp = self.strategy[name][1]
            if not check_mtime(self.source_container.mtime(name), timestamp, self.ttl):
                try:
                    del self.strategy[name]
                except KeyError:    # entry already removed
                    pass
                removed += 1
        return removed

    def clear(self) -> None:
        """remove all sources from the cache"""
        self.strategy.clear()


class MemoryCacheStrategy(MutableMapping[K, V]):
    """caching strategies to be used with MemoryCache"""
    __slots__ = ()

    @abstractmethod
    def peek(self, key: K) -> V:
        """get the value of key without triggering side effects like changing its priority"""
        raise NotImplementedError


class UnboundedCacheStrategy(Dict[K, V], MemoryCacheStrategy[K, V]):
    """strategy without a size limit"""

    __slots__ = ()

    def peek(self, key: K) -> V:
        """since this strategy has no size limit this method is identical to __getitem__"""
        return self[key]


class LRUCacheStrategy(MemoryCacheStrategy[K, V]):
    """strategy which enforces a size limit with LRU"""
    __slots__ = ("storage", "lock", "max_entries")

    storage: OrderedDict[K, V]

    lock: Lock  # OrderedDict is not thread safe

    max_entries: int

    def __init__(self, max_entries: int) -> None:
        self.storage = OrderedDict()
        self.lock = Lock()
        self.max_entries = max_entries

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LRUCacheStrategy):
            return self.storage == other.storage \
                and self.max_entries == other.max_entries
        return NotImplemented

    def __getitem__(self, key: K) -> V:
        """get a value, setting it as the most recently used one"""
        with self.lock:
            self.storage.move_to_end(key, last=False)   # higher index = longer time since last use
            return self.storage[key]

    def __setitem__(self, key: K, value: V) -> None:
        """set a value, removing old ones if necessary"""
        with self.lock:
            if key not in self.storage and len(self.storage) == self.max_entries:
                self.storage.popitem()  # make space for new entry by removing the last element
            self.storage[key] = value

    def __delitem__(self, key: K) -> None:
        """remove a value"""
        with self.lock:
            del self.storage[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self.storage)

    def __len__(self) -> int:
        return len(self.storage)

    def __contains__(self, key: object) -> bool:
        return key in self.storage

    def keys(self) -> KeysView[K]:
        return self.storage.keys()

    def values(self) -> ValuesView[V]:
        return self.storage.values()

    def items(self) -> ItemsView[K, V]:
        return self.storage.items()

    def peek(self, key: K) -> V:
        """get the value of key without triggering side effects like changing its priority"""
        with self.lock:
            return self.storage[key]

    @overload
    def pop(self, key: K) -> V:
        ...

    @overload
    def pop(self, key: K, default: Union[V, T] = ...) -> Union[V, T]:
        ...

    def pop(self, key: K, default: Union[V, T] = POP_SENTINEL) -> Union[V, T]:     # type: ignore
        """remove a value and return it"""
        with self.lock:
            if default is POP_SENTINEL:
                return self.storage.pop(key)
            return self.storage.pop(key, default)

    def popitem(self) -> Tuple[K, V]:
        """remove the least recently used key-value pair and return it"""
        with self.lock:
            return self.storage.popitem()

    def clear(self) -> None:
        """remove all values"""
        with self.lock:
            self.storage.clear()
