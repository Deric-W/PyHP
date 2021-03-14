#!/usr/bin/python3

"""Tests for pyhp.backends.caches.timestamped.memory"""

import unittest
import re
import io
import os
import os.path
import time
from pyhp.backends.files import FileSource, Directory
from pyhp.backends.caches import NotCachedException
from pyhp.backends.caches.timestamped.memory import (
    MemoryCacheSource,
    MemoryCache,
    UnboundedCacheStrategy,
    LRUCacheStrategy
)
from pyhp.compiler.parsers import RegexParser
from pyhp.compiler.generic import GenericCodeBuilder
from pyhp.compiler.util import Compiler, Dedenter


compiler = Compiler(
    RegexParser(
        re.compile(r"<\?pyhp\s"),
        re.compile(r"\s\?>")
    ),
    Dedenter(
        GenericCodeBuilder(-1)
    )
)

compiler2 = Compiler(
    RegexParser(
        re.compile(r"<\?pyhp\s"),
        re.compile(r"\s\?>")
    ),
    GenericCodeBuilder(0)   # different than compiler!
)


class TestMemoryCacheSource(unittest.TestCase):
    """test MemoryCacheSource"""

    def test_eq(self) -> None:
        """test MemoryCacheSource.__eq__"""
        strategy = UnboundedCacheStrategy()
        sources = [
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "test",
                strategy
            ),
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler2
                ),
                "test",
                strategy
            ),
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "test2",
                strategy
            ),
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "test",
                LRUCacheStrategy(9)
            ),
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "test",
                strategy,
                9
            )
        ]
        try:
            for source in sources:
                self.assertEqual(
                    [source],
                    [s for s in sources if s == source]
                )
        finally:
            for source in sources:
                source.close()

    def test_code(self) -> None:
        """test MemoryCacheSource.code"""
        strategy = UnboundedCacheStrategy()
        with MemoryCacheSource(
            FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler),
            "test",
            strategy,
            int(1e9)
        ) as source:
            self.assertNotIn("test", strategy)
            code1 = source.code()
            self.assertIn("test", strategy)
            self.assertEqual(code1, source.code())   # check if source can be read multiple times
            time.sleep(1.5)
            self.assertEqual(code1, source.code())

    def test_cached(self) -> None:
        """test MemoryCacheSource.cached"""
        strategy = UnboundedCacheStrategy()
        with MemoryCacheSource(
            FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler),
            "test",
            strategy,
            int(1e9)
        ) as source:
            self.assertFalse(source.cached())
            source.fetch()
            self.assertTrue(source.cached())
            time.sleep(1.5)
            self.assertFalse(source.cached())
            source.fetch()
            strategy["test"] = (strategy["test"][0], 0)
            self.assertFalse(source.cached())

    def test_clear(self) -> None:
        """test MemoryCacheSource.clear"""
        strategy = UnboundedCacheStrategy()
        with MemoryCacheSource(
            FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler),
            "test",
            strategy
        ) as source:
            source.fetch()
            self.assertIn("test", strategy)
            source.clear()
            self.assertNotIn("test", strategy)
            with self.assertRaises(NotCachedException):
                source.clear()


class TestMemoryCache(unittest.TestCase):
    """test MemoryCache"""

    def test_from_config(self) -> None:
        """test MemoryCache.from_config"""
        container = Directory("tests/embedding", compiler)
        with MemoryCache.from_config({}, container) as cache:
            self.assertEqual(cache.source_container, container)
            self.assertEqual(cache.ttl, 0)
        with MemoryCache.from_config(
            {"ttl": 9.9},
            Directory("tests/embedding", compiler)
        ) as cache:
            self.assertEqual(cache.ttl, int(9.9e9))
        with MemoryCache.from_config(
            {"strategy": "unbounded"},
            Directory("tests/embedding", compiler)
        ) as cache:
            self.assertIsInstance(cache.strategy, UnboundedCacheStrategy)
        with MemoryCache.from_config(
            {"strategy": "lru", "max_entries": 9},
            Directory("tests/embedding", compiler)
        ) as cache:
            self.assertIsInstance(cache.strategy, LRUCacheStrategy)
        with self.assertRaises(ValueError):
            MemoryCache.from_config({"ttl": "a"}, container)
        with self.assertRaises(ValueError):
            MemoryCache.from_config({"strategy": "test"}, container)
        with self.assertRaises(ValueError):
            MemoryCache.from_config({"strategy": "lru", "max_entries": "a"}, container)
        with self.assertRaises(ValueError):
            MemoryCache.from_config({}, compiler)

    def test_eq(self) -> None:
        """test MemoryCache.__eq__"""
        strategy1 = UnboundedCacheStrategy()
        strategy2 = LRUCacheStrategy(9)
        with MemoryCache(Directory("tests/embedding", compiler), strategy1) as cache1, \
                MemoryCache(Directory("tests/embedding", compiler2), strategy1) as cache2, \
                MemoryCache(Directory("tests/embedding", compiler), strategy1, 9) as cache3, \
                MemoryCache(Directory("tests/embedding", compiler), strategy2) as cache4:
            self.assertEqual(cache1, cache1)
            self.assertNotEqual(cache1, cache2)
            self.assertNotEqual(cache2, cache3)
            self.assertNotEqual(cache3, cache4)

    def test_access(self) -> None:
        """test MemoryCache.__getitem__"""
        with MemoryCache(
            Directory("tests/embedding", compiler),
            UnboundedCacheStrategy(),
            9
        ) as cache, cache["syntax.pyhp"] as source:
            self.assertEqual(source.name, "syntax.pyhp")
            self.assertIs(source.strategy, cache.strategy)
            self.assertEqual(source.ttl, 9)
            self.assertEqual(
                os.path.normpath(source.code_source.fd.name),
                os.path.normpath("tests/embedding/syntax.pyhp")
            )

    def test_gc_clear(self) -> None:
        """test FileCache.gc and FileCache.clear"""
        with MemoryCache(Directory("tests/embedding", compiler), UnboundedCacheStrategy()) as cache:
            with cache["syntax.pyhp"] as source:
                source.fetch()
            with cache["shebang.pyhp"] as source:
                source.fetch()
            cache.strategy["shebang.pyhp"] = (cache.strategy["shebang.pyhp"][0], 0)
            self.assertEqual(cache.gc(), 1)
            self.assertIn("syntax.pyhp", cache.strategy)
            self.assertNotIn("shebang.pyhp", cache.strategy)
            cache.clear()
            self.assertEqual(len(cache.strategy), 0)


class TestUnboundedCacheStrategy(unittest.TestCase):
    """test UnboundedCacheStrategy"""

    def test_peek(self) -> None:
        """test UnboundedCacheStrategy.peek"""
        strategy1 = UnboundedCacheStrategy()
        strategy2 = UnboundedCacheStrategy()
        strategy1["test"] = "Test"
        strategy2["test"] = "Test"
        self.assertEqual(strategy1.peek("test"), "Test")
        self.assertEqual(strategy1.peek("test"), "Test")    # no side effects
        self.assertEqual(strategy1, strategy2)


class TestLRUCacheStrategy(unittest.TestCase):
    """test LRUCacheStrategy"""

    def test_eq(self) -> None:
        """test LRUCacheStrategy.__eq__"""
        strategy1 = LRUCacheStrategy(1)
        strategy2 = LRUCacheStrategy(2)
        self.assertEqual(strategy1, strategy1)
        self.assertNotEqual(strategy1, strategy2)
        self.assertNotEqual(1, strategy2)

    def test_lru(self) -> None:
        """test LRUCacheStrategy get, set and del"""
        strategy = LRUCacheStrategy(3)
        strategy["a"] = 1
        strategy["b"] = 2
        strategy["c"] = 3
        self.assertEqual(len(strategy), 3)
        self.assertIn("a", strategy)
        self.assertIn("b", strategy)
        self.assertIn("c", strategy)
        self.assertEqual(strategy["b"], 2)
        strategy["d"] = 4
        self.assertEqual(len(strategy), 3)
        self.assertIn("a", strategy)
        self.assertIn("b", strategy)
        self.assertNotIn("c", strategy)
        self.assertIn("d", strategy)
        del strategy["a"]
        self.assertNotIn("a", strategy)

    def test_peek(self) -> None:
        """test LRUCacheStrategy.peek"""
        strategy1 = LRUCacheStrategy(3)
        strategy2 = LRUCacheStrategy(3)
        strategy1["test"] = "Test"
        strategy2["test"] = "Test"
        self.assertEqual(strategy1.peek("test"), "Test")
        self.assertEqual(strategy1.peek("test"), "Test")    # no side effects
        self.assertEqual(strategy1, strategy2)

    def test_pop(self) -> None:
        """test LRUCacheStrategy.pop and popitem"""
        strategy = LRUCacheStrategy(3)
        strategy["a"] = 1
        strategy["b"] = 2
        strategy["c"] = 3
        self.assertEqual(strategy.pop("a"), 1)
        self.assertNotIn("a", strategy)
        with self.assertRaises(KeyError):
            strategy.pop("a")
        self.assertEqual(strategy.pop("a", 2), 2)
        self.assertEqual(strategy.popitem(), ("c", 3))
        self.assertEqual(strategy.popitem(), ("b", 2))
        with self.assertRaises(KeyError):
            strategy.popitem()

    def test_views(self) -> None:
        """test LRUCacheStrategy keys, values and items"""
        strategy = LRUCacheStrategy(3)
        strategy["a"] = 1
        strategy["b"] = 2
        strategy["c"] = 3
        self.assertEqual(list(strategy), ["a", "b", "c"])
        self.assertEqual(list(strategy.keys()), ["a", "b", "c"])
        self.assertEqual(list(strategy.values()), [1, 2, 3])
        self.assertEqual(list(strategy.items()), [("a", 1), ("b", 2), ("c", 3)])

    def test_clear(self) -> None:
        """test LRUCacheStrategy.clear"""
        strategy = LRUCacheStrategy(3)
        strategy["a"] = 1
        strategy["b"] = 2
        strategy["c"] = 3
        strategy.clear()
        self.assertEqual(len(strategy), 0)
        strategy.clear()    # check for exceptions
