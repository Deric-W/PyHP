#!/usr/bin/python3

"""Tests for pyhp.caching.util"""

import re
import unittest
import unittest.mock
from pyhp.caching import util, memory
from pyhp.compiler.parsers import RegexParser
from pyhp.compiler.generic import GenericCodeBuilder
from pyhp.compiler.util import Compiler


compiler = Compiler(
    RegexParser(
        re.compile(r"<\?pyhp\s"),
        re.compile(r"\s\?>")
    ),
    GenericCodeBuilder(-1)
)
compiler2 = Compiler(
    RegexParser(
        re.compile("a"),
        re.compile("b")
    ),
    GenericCodeBuilder(-1)
)


class DummyConfigBuilder(util.ConfigHierarchyBuilder):
    """builder used for tests"""
    add_name = unittest.mock.Mock()


class TestHierarchyBuilder(unittest.TestCase):
    """tests for HierarchyBuilder"""
    def test_eq(self) -> None:
        """test HierarchyBuilder.__eq__"""
        builder1 = util.HierarchyBuilder(compiler)
        builder2 = util.HierarchyBuilder(compiler2)
        builder3 = util.HierarchyBuilder(compiler2)
        builder3.add_container(memory.MemorySourceContainer, {})
        self.assertEqual(
            [builder1],
            [b for b in (builder1, builder2, builder3) if b == builder1]
        )

    def test_building(self) -> None:
        """test building a hierarchy"""
        builder = util.HierarchyBuilder(compiler)
        builder.add_container(memory.MemorySourceContainer, {})
        with self.assertRaises(ValueError):
            builder.add_container(memory.MemorySourceContainer, {})
        hierarchy = builder.hierarchy()
        self.assertIsInstance(hierarchy, memory.MemorySourceContainer)
        self.assertEqual(hierarchy, builder.pop())
        with self.assertRaises(IndexError):
            builder.pop()

    def test_copy(self) -> None:
        """test HierarchyBuilder.copy"""
        builder = util.HierarchyBuilder(compiler)
        builder2 = builder.copy()
        self.assertEqual(builder, builder2)
        builder.add_container(memory.MemorySourceContainer, {})
        self.assertNotEqual(builder, builder2)
        self.assertEqual(builder, builder.copy())


class TestConfigHierarchyBuilder(unittest.TestCase):
    """tests for ConfigHierarchyBuilder"""
    def test_add_config(self) -> None:
        """test ConfigHierarchyBuilder.add_config"""
        config = {
            "test1": {},
            "test2": {"a": 1, "b": 2}
        }
        builder = DummyConfigBuilder(compiler)
        builder.add_config(config)
        builder.add_name.assert_has_calls([
            unittest.mock.call("test1", config["test1"]),
            unittest.mock.call("test2", config["test2"])
        ])
        with self.assertRaises(ValueError):
            builder.add_config({
                "test3": 9001
            })


class TestModuleHierarchyBuilder(unittest.TestCase):
    """tests for ModuleHierarchyBuilder"""
    def test_add_name(self) -> None:
        """test ModuleHierarchyBuilder.add_name"""
        builder = util.ModuleHierarchyBuilder(compiler)
        builder2 = util.HierarchyBuilder(compiler)
        builder.add_name("pyhp.caching.memory.MemorySourceContainer", {})
        builder2.add_container(memory.MemorySourceContainer, {})
        self.assertEqual(builder, builder2)


class TestPathHierarchyBuilder(unittest.TestCase):
    """tests for PathHierarchyBuilder"""
    def test_add_name(self) -> None:
        """test PathHierarchyBuilder.add_name"""
        builder = util.PathHierarchyBuilder(compiler)
        builder2 = util.HierarchyBuilder(compiler)
        builder.add_name("tests/caching/dummy.py:MemorySourceContainer", {})
        builder2.add_container(memory.MemorySourceContainer, {})
        self.assertEqual(builder, builder2)
