#!/usr/bin/python3

"""Uni tests for the abc"""

import re
import unittest
import unittest.mock
from typing import Mapping, Any
from pyhp.caching import (
    SourceInfo,
    CodeSource,
    DirectCodeSource,
    TimestampedCodeSource,
    CacheSource,
    NotCachedException,
    CodeSourceContainer,
    TimestampedCodeSourceContainer,
    CacheSourceContainer,
    CachedMapping
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
        self.assertNotIn(99, container)

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
            value.__exit__ = context_manager_exit
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
            source.__exit__ = context_manager_exit
            self.assertIn((name, source), items)
            source.close.assert_called()
        self.assertNotIn(("a", 1), items)
        self.assertNotIn(("abc", 1), items)
        self.assertNotIn((1, 2), items)


class TestTimestampedCodeSourceContainer(unittest.TestCase):
    """test TimestampedCodeSourceContainer"""
    def test_mtime(self) -> None:
        """test TimestampedCodeSourceContainer.mtime"""
        container = {
            "a": unittest.mock.MagicMock(spec_set=TimestampedCodeSource)
        }
        container["a"].__enter__ = lambda x: x
        container["a"].__exit__ = context_manager_exit
        container["a"].mtime.configure_mock(side_effect=(9,))
        self.assertEqual(TimestampedCodeSourceContainer.mtime(container, "a"), 9)
        container["a"].close.assert_called()
        with self.assertRaises(KeyError):
            TimestampedCodeSourceContainer.mtime(container, "b")

    def test_ctime(self) -> None:
        """test TimestampedCodeSourceContainer.ctime"""
        container = {
            "a": unittest.mock.MagicMock(spec_set=TimestampedCodeSource)
        }
        container["a"].__enter__ = lambda x: x
        container["a"].__exit__ = context_manager_exit
        container["a"].ctime.configure_mock(side_effect=(9,))
        self.assertEqual(TimestampedCodeSourceContainer.ctime(container, "a"), 9)
        container["a"].close.assert_called()
        with self.assertRaises(KeyError):
            TimestampedCodeSourceContainer.ctime(container, "b")

    def test_atime(self) -> None:
        """test TimestampedCodeSourceContainer.atime"""
        container = {
            "a": unittest.mock.MagicMock(spec_set=TimestampedCodeSource)
        }
        container["a"].__enter__ = lambda x: x
        container["a"].__exit__ = context_manager_exit
        container["a"].atime.configure_mock(side_effect=(9,))
        self.assertEqual(TimestampedCodeSourceContainer.atime(container, "a"), 9)
        container["a"].close.assert_called()
        with self.assertRaises(KeyError):
            TimestampedCodeSourceContainer.atime(container, "b")

    def test_info(self) -> None:
        """test TimestampedCodeSourceContainer.info"""
        info = SourceInfo(1, 2, 3)
        container = {
            "a": unittest.mock.MagicMock(spec_set=TimestampedCodeSource)
        }
        container["a"].__enter__ = lambda x: x
        container["a"].__exit__ = context_manager_exit
        container["a"].info.configure_mock(side_effect=(info,))
        self.assertEqual(TimestampedCodeSourceContainer.info(container, "a"), info)
        container["a"].close.assert_called()
        with self.assertRaises(KeyError):
            TimestampedCodeSourceContainer.info(container, "b")


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

    def test_cached(self) -> None:
        """test CacheSourceContainer.cached"""
        self.assertIsInstance(CacheSourceContainer.cached({}), Mapping)


class TestCachedMapping(unittest.TestCase):
    """test CachedMapping"""
    def test_getitem(self) -> None:
        """test CachedMapping.__getitem__"""
        container = {
            "a": unittest.mock.Mock(spec_set=CacheSource),
            "b": unittest.mock.Mock(spec_set=CacheSource),
            "c": unittest.mock.Mock(spec_set=CacheSource)
        }
        container["a"].cached.configure_mock(side_effect=(True,))
        container["b"].cached.configure_mock(side_effect=(False,))
        container["c"].cached.configure_mock(side_effect=(RuntimeError,))
        mapping = CachedMapping(container)
        self.assertEqual(mapping["a"], container["a"])
        with self.assertRaises(KeyError):
            mapping["b"]
        container["b"].close.assert_called()
        with self.assertRaises(RuntimeError):
            mapping["c"]
        container["c"].close.assert_called()

    def test_iter(self) -> None:
        """test CachedMapping.__iter__"""
        container = {
            "a": unittest.mock.Mock(spec_set=CacheSource),
            "b": unittest.mock.Mock(spec_set=CacheSource),
            "c": unittest.mock.Mock(spec_set=CacheSource)
        }
        container["a"].cached.configure_mock(side_effect=(True,))
        container["b"].cached.configure_mock(side_effect=(False,))
        container["c"].cached.configure_mock(side_effect=(RuntimeError,))
        iterator = iter(CachedMapping(container))
        names = []
        while True:
            try:
                names.append(next(iterator))
            except RuntimeError:
                pass
            except StopIteration:
                break
        self.assertEqual(names, ["a"])
        for mock in container.values():
            mock.close.assert_called()

    def test_len(self) -> None:
        """test CachedMapping.__len__"""
        container = {
            "a": unittest.mock.Mock(spec_set=CacheSource),
            "b": unittest.mock.Mock(spec_set=CacheSource),
            "c": unittest.mock.Mock(spec_set=CacheSource)
        }
        container["a"].cached.configure_mock(side_effect=(True,))
        container["b"].cached.configure_mock(side_effect=(False,))
        container["c"].cached.configure_mock(side_effect=(True,))
        self.assertEqual(len(CachedMapping(container)), 2)

    def test_contains(self) -> None:
        """test CachedMapping.__contains__"""
        container = {
            "a": unittest.mock.MagicMock(spec_set=CacheSource),
            "b": unittest.mock.MagicMock(spec_set=CacheSource),
            "c": unittest.mock.MagicMock(spec_set=CacheSource)
        }
        container["a"].cached.configure_mock(side_effect=(True,))
        container["b"].cached.configure_mock(side_effect=(False,))
        container["c"].cached.configure_mock(side_effect=(RuntimeError,))
        for mock in container.values():
            mock.__enter__ = lambda x: x
            mock.__exit__ = context_manager_exit
        mapping = CachedMapping(container)
        self.assertIn("a", mapping)
        self.assertNotIn("b", mapping)
        with self.assertRaises(RuntimeError):
            "c" in mapping
        self.assertNotIn("d", mapping)
        self.assertNotIn(9, mapping)
        for mock in container.values():
            mock.close.assert_called()

    def test_values(self) -> None:
        """test CachedMapping.values"""
        container = {
            "a": unittest.mock.Mock(spec_set=CacheSource),
            "b": unittest.mock.Mock(spec_set=CacheSource),
            "c": unittest.mock.Mock(spec_set=CacheSource)
        }
        container["a"].cached.configure_mock(side_effect=(True,))
        container["b"].cached.configure_mock(side_effect=(False,))
        container["c"].cached.configure_mock(side_effect=(RuntimeError,))
        iterator = iter(CachedMapping(container).values())
        values = []
        while True:
            try:
                values.append(next(iterator))
            except RuntimeError:
                pass
            except StopIteration:
                break
        self.assertEqual(values, [container["a"]])
        container["b"].close.assert_called()
        container["c"].close.assert_called()

    def test_items(self) -> None:
        """test CachedMapping.items"""
        container = {
            "a": unittest.mock.Mock(spec_set=CacheSource),
            "b": unittest.mock.Mock(spec_set=CacheSource),
            "c": unittest.mock.Mock(spec_set=CacheSource)
        }
        container["a"].cached.configure_mock(side_effect=(True,))
        container["b"].cached.configure_mock(side_effect=(False,))
        container["c"].cached.configure_mock(side_effect=(RuntimeError,))
        iterator = iter(CachedMapping(container).items())
        items = []
        while True:
            try:
                items.append(next(iterator))
            except RuntimeError:
                pass
            except StopIteration:
                break
        self.assertEqual(items, [("a", container["a"])])
        container["b"].close.assert_called()
        container["c"].close.assert_called()


def context_manager_exit(self: Any, *_args: Any) -> None:
    self.close()
