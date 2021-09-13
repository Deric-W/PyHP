#!/usr/bin/python3

"""Uni tests for the abc"""

import unittest
import unittest.mock
from typing import Mapping, Any
from pyhp.backends.caches import (
    CacheSource,
    CacheSourceContainer,
    CachedMapping
)


def context_manager_exit(self: Any, *_args: Any) -> None:
    self.close()


class TestCacheSource(unittest.TestCase):
    """test the cache source abc methods"""
    def test_gc(self) -> None:
        """test CacheSource.gc"""
        source = unittest.mock.Mock(spec_set=CacheSource)
        source.cached.configure_mock(side_effect=(False, False, True))
        source.clear.configure_mock(side_effect=(False, True, True))
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


class TestCacheSourceContainer(unittest.TestCase):
    """test CacheSourceContainer"""
    def test_magic_methods(self) -> None:
        """test __contains__, __iter__, __getitem__ and __len__"""
        container = unittest.mock.MagicMock(spec_set=CacheSourceContainer)
        CacheSourceContainer.__contains__(container, 1)
        container.source_container.__contains__.assert_called()
        CacheSourceContainer.__iter__(container)
        container.source_container.__iter__.assert_called()
        CacheSourceContainer.__getitem__(container, "test")
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
        cached["b"].clear.configure_mock(side_effect=(False,))
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

    def test_eq(self) -> None:
        """test CachedMapping.__eq__"""
        mapping1 = CachedMapping({"a": 1})
        mapping2 = CachedMapping({"b": 2})
        self.assertEqual(mapping1, mapping1)
        self.assertNotEqual(mapping1, mapping2)
        self.assertNotEqual(1, mapping2)

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
