#!/usr/bin/python3

"""Uni tests for the abc"""

import re
import unittest
from typing import Iterator, Mapping
from pyhp.caching import (
    SourceInfo,
    DirectCodeSource,
    TimestampedCodeSource,
    CacheSource,
    NotCachedException,
    CodeSourceContainer,
    CacheSourceContainer,
)
from pyhp.compiler import Code


PATTERN = re.compile(r"a|b")


class TestSource(unittest.TestCase, DirectCodeSource, TimestampedCodeSource):
    """test the source abc methods"""
    def mtime(self) -> int:
        return 99

    def ctime(self) -> int:
        return 10

    def atime(self) -> int:
        return -9

    def test_info(self) -> None:
        """test TimestampedCodeSource.info"""
        self.assertEqual(
            self.info(),
            SourceInfo(
                99,
                10,
                -9
            )
        )

    def source(self) -> str:
        return "test"

    def test_size(self) -> None:
        """test DirectCodeSource.size"""
        self.assertEqual(self.size(), 4)

    def code(self) -> Code:
        raise RuntimeError

    def close(self) -> None:
        raise RuntimeError


class TestCacheSource(unittest.TestCase, CacheSource[TestSource]):
    """test the cache source abc methods"""
    code_source = TestSource()

    is_cached: bool = False

    is_clear: bool = False

    def cached(self) -> bool:
        return self.is_cached

    def clear(self) -> None:
        if self.is_clear:
            raise NotCachedException

    def test_gc(self) -> None:
        """test CacheSource.gc"""
        self.is_cached = False
        self.is_clear = True
        self.assertEqual(self.gc(), False)
        self.is_clear = False
        self.assertEqual(self.gc(), True)
        self.is_cached = True
        self.is_clear = False
        self.assertEqual(self.gc(), False)

    def test_close(self) -> None:
        """test CodeSourceDecorator.close"""
        with self.assertRaises(RuntimeError):
            self.close()

    def test_code(self) -> None:
        """test CodeSourceDecorator.code"""
        with self.assertRaises(RuntimeError):
            self.code()


class TestSourceContainer(unittest.TestCase, CodeSourceContainer[TestSource]):
    """test the code source container abc"""
    sources = {
        "a": TestSource(),
        "b": TestSource(),
        "c": TestSource()
    }

    @classmethod
    def from_config(cls, config, before):
        raise NotImplementedError

    def __getitem__(self, key: str) -> TestSource:
        return self.sources[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.sources)

    def __len__(self) -> int:
        return len(self.sources)

    def test_search(self) -> None:
        """test CodeSourceContainer.search"""
        self.assertEqual(
            list(self.search(PATTERN)),
            [
                ("a", self.sources["a"]),
                ("b", self.sources["b"])
            ]
        )

    def close(self) -> None:
        raise RuntimeError


class TestCacheSourceContainer(unittest.TestCase, CacheSourceContainer[TestSourceContainer, TestCacheSource]):
    """test the cache source container abc"""
    sources = {
        "a": TestCacheSource(),
        "b": TestCacheSource(),
        "c": TestCacheSource()
    }

    source_container = TestSourceContainer()

    @classmethod
    def from_config(cls, config, before):
        raise NotImplementedError

    def __getitem__(self, key: str) -> TestCacheSource:
        return self.sources[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.sources)

    def __len__(self) -> int:
        return len(self.sources)

    def cached(self) -> Mapping[str, TestCacheSource]:
        return {
            "a": self["a"],
            "c": self["c"]
        }

    def test_gc(self) -> None:
        """test CacheSourceContainer.gc"""
        self.assertEqual(self.gc(), 3)

    def test_clear(self) -> None:
        """test CacheSourceContainer.clear"""
        self.clear()    # should not raise any exceptions

    def test_close(self) -> None:
        """test CodeSourceContainerDecorator.close"""
        with self.assertRaises(RuntimeError):
            self.close()
