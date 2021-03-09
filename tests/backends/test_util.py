#!/usr/bin/python3

"""Tests for pyhp.backends.util"""

import re
import unittest
import unittest.mock
from pyhp.backends import util, memory, files
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
        builder3.add_container(memory.HashMap, {})
        self.assertEqual(
            [builder1],
            [b for b in (builder1, builder2, builder3) if b == builder1]
        )

    def test_building(self) -> None:
        """test building a hierarchy"""
        builder = util.HierarchyBuilder(compiler)
        builder.add_container(memory.HashMap, {})
        with self.assertRaises(ValueError):
            builder.add_container(files.Directory, {"path": "test"})
        hierarchy = builder.hierarchy()
        self.assertIsInstance(hierarchy, memory.HashMap)
        self.assertEqual(hierarchy, builder.pop())
        with self.assertRaises(IndexError):
            builder.pop()

    def test_copy(self) -> None:
        """test HierarchyBuilder.copy"""
        builder = util.HierarchyBuilder(compiler)
        builder2 = builder.copy()
        self.assertEqual(builder, builder2)
        builder.add_container(memory.HashMap, {})
        self.assertNotEqual(builder, builder2)
        self.assertEqual(builder, builder.copy())


class TestConfigHierarchyBuilder(unittest.TestCase):
    """tests for ConfigHierarchyBuilder"""
    def test_add_config(self) -> None:
        """test ConfigHierarchyBuilder.add_config"""
        config = [
            {
                "name": "test1",
                "config": {}
            },
            {
                "name": "test2",
                "config": {"a": 1, "b": 2}
            }
        ]
        builder = DummyConfigBuilder(compiler)
        builder.add_config(config)
        builder.add_name.assert_has_calls([
            unittest.mock.call("test1", config[0]["config"]),
            unittest.mock.call("test2", config[1]["config"])
        ])
        with self.assertRaises(ValueError):
            builder.add_config([
                {
                    "name": 9001,
                    "config": {}
                }
            ])
        with self.assertRaises(ValueError):
            builder.add_config([
                {
                    "name": "test4",
                    "config": 9001
                }
            ])


class TestModuleHierarchyBuilder(unittest.TestCase):
    """tests for ModuleHierarchyBuilder"""
    def test_add_name(self) -> None:
        """test ModuleHierarchyBuilder.add_name"""
        builder = util.ModuleHierarchyBuilder(compiler)
        builder2 = util.HierarchyBuilder(compiler)
        builder.add_name("pyhp.backends.memory.HashMap", {})
        builder2.add_container(memory.HashMap, {})
        self.assertEqual(builder, builder2)


class TestPathHierarchyBuilder(unittest.TestCase):
    """tests for PathHierarchyBuilder"""
    def test_add_name(self) -> None:
        """test PathHierarchyBuilder.add_name"""
        builder = util.PathHierarchyBuilder(compiler)
        builder2 = util.HierarchyBuilder(compiler)
        builder.add_name("tests/backends/dummy.py:HashMap", {})
        builder2.add_container(memory.HashMap, {})
        self.assertEqual(builder, builder2)
