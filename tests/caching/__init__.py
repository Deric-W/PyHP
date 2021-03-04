#!/usr/bin/python3

"""Uni tests for the abc"""

import re
import unittest
import unittest.mock
from typing import Iterator, Mapping
from pyhp.caching import (
    SourceInfo,
    CodeSource,
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


class TestCacheSource(unittest.TestCase):
    """test the cache source abc methods"""
    def test_gc(self) -> None:
        """test CacheSource.gc"""
        source = unittest.mock.Mock(spec_set=CacheSource)
        source.cached.configure_mock(side_effect=(False, False, True))
        source.clear.configure_mock(side_effect=(NotCachedException, None, None))
        self.assertEqual(CacheSource.gc(source), False)
        self.assertEqual(CacheSource.gc(source), True)
        self.assertEqual(CacheSource.gc(source), False)

    def test_close(self) -> None:
        """test CodeSourceDecorator.close"""
        source = unittest.mock.Mock(spec_set=CacheSource)
        source.detach.configure_mock(side_effect=(source.code_source,))
        CacheSource.close(source)
        source.detach.assert_called()
        source.code_source.close.assert_called()

    def test_code(self) -> None:
        """test CodeSourceDecorator.code"""
        source = unittest.mock.Mock(spec_set=CacheSource)
        CacheSource.code(source)
        source.code_source.code.assert_called()


class TestSourceContainer(unittest.TestCase):
    """test the code source container abc"""
    def test_contains(self) -> None:
        """test CodeSourceContainer.__contains__"""
        source = unittest.mock.Mock(spec_set=CodeSource)
        container = unittest.mock.MagicMock(spec_set=CodeSourceContainer)
        container.__getitem__.configure_mock(side_effect=(source, KeyError))
        self.assertTrue(CodeSourceContainer.__contains__(container, "Test"))
        source.close.assert_called()
        self.assertFalse(CodeSourceContainer.__contains__(container, "Test"))
        with self.assertRaises(TypeError):
            CodeSourceContainer.__contains__(container, 99)

    def test_search(self) -> None:
        """test CodeSourceContainer.search"""
        self.assertEqual(
            list(CodeSourceContainer.search({"a": 1, "b": 2, "c": 3}, PATTERN)),
            [("a", 1), ("b", 2)]
        )

    def test_values(self) -> None:
        """test CodeSourceContainer.values"""
        sources = {
            "a": unittest.mock.MagicMock(spec_set=CodeSource),
            "b": unittest.mock.MagicMock(spec_set=CodeSource),
            "c": unittest.mock.MagicMock(spec_set=CodeSource)
        }
        values = CodeSourceContainer.values(sources)
        for value in sources.values():
            value.__enter__ = lambda x: x
            value.__exit__ = lambda x, *args: x.close()
            self.assertIn(value, values)
            value.close.assert_called()
        self.assertNotIn(1, values)

    def test_items(self) -> None:
        """test CodeSourceContainer.items"""
        sources = {
            "a": unittest.mock.MagicMock(spec_set=CodeSource),
            "b": unittest.mock.MagicMock(spec_set=CodeSource),
            "c": unittest.mock.MagicMock(spec_set=CodeSource)
        }
        items = CodeSourceContainer.items(sources)
        for name, source in sources.items():
            source.__enter__ = lambda x: x
            source.__exit__ = lambda x, *args: x.close()
            self.assertIn((name, source), items)
            source.close.assert_called()
        self.assertNotIn(("a", 1), items)
        self.assertNotIn(("abc", 1), items)
        with self.assertRaises(TypeError):
            1 in items
        with self.assertRaises(TypeError):
            (1, 2) in items


class TestCacheSourceContainer(unittest.TestCase):
    """test CacheSourceContainer"""
    def test_magic_methods(self) -> None:
        """test __contains__, __iter__, __getitem__ and __len__"""
        container = unittest.mock.MagicMock(spec_set=CacheSourceContainer)
        CacheSourceContainer.__contains__(container, 1)
        container.source_container.__contains__.assert_called()
        CacheSourceContainer.__iter__(container)
        container.source_container.__iter__.assert_called()
        CacheSourceContainer.__getitem__(container, 1)
        container.source_container.__getitem__.assert_called()
        CacheSourceContainer.__len__(container)
        container.source_container.__len__.assert_called()

    def test_gc(self) -> None:
        """test CacheSourceContainer.gc"""
        sources = {
            "a": unittest.mock.Mock(spec_set=CacheSource),
            "b": unittest.mock.Mock(spec_set=CacheSource),
            "c": unittest.mock.Mock(spec_set=CacheSource)
        }
        sources["a"].gc.configure_mock(side_effect=(True, True))
        sources["b"].gc.configure_mock(side_effect=(True, False))
        sources["c"].gc.configure_mock(side_effect=(True, True))
        self.assertEqual(CacheSourceContainer.gc(sources), 3)
        for source in sources.values():
            source.gc.assert_called()
        self.assertEqual(CacheSourceContainer.gc(sources), 2)

    def test_clear(self) -> None:
        """test CacheSourceContainer.clear"""
        cached = {
            "a": unittest.mock.Mock(spec_set=CacheSource),
            "b": unittest.mock.Mock(spec_set=CacheSource)
        }
        cached["b"].clear.configure_mock(side_effect=(NotCachedException,))
        container = unittest.mock.Mock(spec_set=CacheSourceContainer)
        container.cached.configure_mock(side_effect=(cached,))
        CacheSourceContainer.clear(container)
        for source in cached.values():
            source.clear.assert_called()

    def test_close(self) -> None:
        """test CodeSourceContainerDecorator.close"""
        container = unittest.mock.Mock(spec_set=CacheSourceContainer)
        container.detach.configure_mock(side_effect=(container.source_container,))
        CacheSourceContainer.close(container)
        container.detach.assert_called()
        container.source_container.close.assert_called()
