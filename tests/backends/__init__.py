#!/usr/bin/python3

"""Uni tests for the abc"""

import unittest
import unittest.mock
from typing import Any
from pyhp.backends import (
    SourceInfo,
    CodeSource,
    DirectCodeSource,
    TimestampedCodeSource,
    CodeSourceContainer,
    TimestampedCodeSourceContainer
)
from pyhp.compiler import Code


def context_manager_exit(self: Any, *_args: Any) -> None:
    self.close()


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
        self.assertFalse(CodeSourceContainer.__contains__(container, 1))

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
