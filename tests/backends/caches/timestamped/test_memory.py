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
    UnboundedMemoryCache
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
        storage = {}
        sources = [
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "test",
                storage
            ),
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler2
                ),
                "test",
                storage
            ),
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "test2",
                storage
            ),
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "test",
                {}
            ),
            MemoryCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "test",
                {},
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
        storage = {}
        with MemoryCacheSource(
            FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler),
            "test",
            storage,
            int(1e9)
        ) as source:
            self.assertNotIn("test", storage)
            code1 = source.code()
            self.assertIn("test", storage)
            self.assertEqual(code1, source.code())   # check if source can be read multiple times
            time.sleep(1.5)
            self.assertEqual(code1, source.code())

    def test_cached(self) -> None:
        """test MemoryCacheSource.cached"""
        storage = {}
        with MemoryCacheSource(
            FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler),
            "test",
            storage,
            int(1e9)
        ) as source:
            self.assertFalse(source.cached())
            source.fetch()
            self.assertTrue(source.cached())
            time.sleep(1.5)
            self.assertFalse(source.cached())
            source.fetch()
            storage["test"] = (storage["test"][0], 0)
            self.assertFalse(source.cached())

    def test_clear(self) -> None:
        """test MemoryCacheSource.clear"""
        storage = {}
        with MemoryCacheSource(
            FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler),
            "test",
            storage
        ) as source:
            source.fetch()
            self.assertIn("test", storage)
            source.clear()
            self.assertNotIn("test", storage)
            with self.assertRaises(NotCachedException):
                source.clear()


class TestUnboundedMemoryCache(unittest.TestCase):
    """test UnboundedMemoryCache"""

    def test_from_config(self) -> None:
        """test UnboundedMemoryCache.from_config"""
        container = Directory("tests/embedding", compiler)
        with UnboundedMemoryCache.from_config({}, container) as cache:
            self.assertEqual(cache.source_container, container)
            self.assertEqual(cache.ttl, 0)
        with UnboundedMemoryCache.from_config(
            {"ttl": 9.9},
            Directory("tests/embedding", compiler)
        ) as cache:
            self.assertEqual(cache.ttl, int(9.9e9))
        with self.assertRaises(ValueError):
            UnboundedMemoryCache.from_config({"ttl": "a"}, container)
        with self.assertRaises(ValueError):
            UnboundedMemoryCache.from_config({}, compiler)

    def test_eq(self) -> None:
        """test UnboundedMemoryCache.__eq__"""
        with UnboundedMemoryCache(Directory("tests/embedding", compiler)) as cache1, \
                UnboundedMemoryCache(Directory("tests/embedding", compiler2)) as cache2, \
                UnboundedMemoryCache(Directory("tests/embedding", compiler), 9) as cache3:
            self.assertEqual(cache1, cache1)
            self.assertNotEqual(cache1, cache2)
            self.assertNotEqual(cache2, cache3)

    def test_access(self) -> None:
        """test UnboundedMemoryCache.__getitem__"""
        with UnboundedMemoryCache(Directory("tests/embedding", compiler), 9) as cache, \
                cache["syntax.pyhp"] as source:
            self.assertEqual(source.name, "syntax.pyhp")
            self.assertIs(source.storage, cache.storage)
            self.assertEqual(source.ttl, 9)
            self.assertEqual(
                os.path.normpath(source.code_source.fd.name),
                os.path.normpath("tests/embedding/syntax.pyhp")
            )

    def test_gc_clear(self) -> None:
        """test FileCache.gc and FileCache.clear"""
        with UnboundedMemoryCache(Directory("tests/embedding", compiler)) as cache:
            with cache["syntax.pyhp"] as source:
                source.fetch()
            with cache["shebang.pyhp"] as source:
                source.fetch()
            cache.storage["shebang.pyhp"] = (cache.storage["shebang.pyhp"][0], 0)
            print(cache.storage)
            self.assertEqual(cache.gc(), 1)
            self.assertIn("syntax.pyhp", cache.storage)
            self.assertNotIn("shebang.pyhp", cache.storage)
            cache.clear()
            self.assertEqual(len(cache.storage), 0)
