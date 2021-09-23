#!/usr/bin/python3

"""Tests for pyhp.backends.util"""

import re
import unittest
import unittest.mock
from pyhp.backends import util, memory, files, CodeSourceContainer
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

dummy = unittest.mock.Mock(spec=CodeSourceContainer)
dummy.from_config.configure_mock(side_effect=lambda c, b: dummy)


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
        self.assertNotEqual(builder1, 42)

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

    def test_close_on_error(self) -> None:
        """test HierarchyBuilder.close_on_error"""
        builder = util.HierarchyBuilder(compiler)
        with self.assertRaises(RuntimeError):
            with builder.close_on_error():
                raise RuntimeError  # test behavior if not containers where constructed
        dummy = unittest.mock.Mock(spec=CodeSourceContainer)
        dummy.from_config.configure_mock(side_effect=lambda b, c: dummy)
        broken_dummy = unittest.mock.Mock(spec=CodeSourceContainer)
        broken_dummy.from_config.configure_mock(side_effect=RuntimeError)
        with self.assertRaises(RuntimeError):
            with builder.close_on_error() as context_result:
                self.assertIs(builder, context_result)
                builder.add_container(dummy, {})
                builder.add_container(broken_dummy, {})
        with builder.close_on_error():
            pass
        dummy.close.assert_called_once()


class TestHierarchyContext(unittest.TestCase):
    """test for HierarchyContext"""
    # HierarchyContext.__exit__ is being tested in TestHierarchyBuilder.close_on_error

    def test_eq(self) -> None:
        """test HierarchyContext.__eq__"""
        contexts = [
            util.HierarchyContext(util.HierarchyBuilder(compiler)),
            util.HierarchyContext(util.PathHierarchyBuilder(compiler2)),
            42
        ]
        self.assertEqual([contexts[0]], [i for i in contexts if i == contexts[0]])


class TestConfigHierarchyBuilder(unittest.TestCase):
    """tests for ConfigHierarchyBuilder"""
    def test_add_config(self) -> None:
        """test ConfigHierarchyBuilder.add_config"""
        config = [
            {
                "name": "test1"
            },
            {
                "name": "test2",
                "config": {"a": 1, "b": 2}
            }
        ]
        builder = DummyConfigBuilder(compiler)
        builder.add_config(config)
        builder.add_name.assert_has_calls([
            unittest.mock.call("test1", {}),
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
        with self.assertRaises(ImportError):
            builder.add_name("not_in_use.txt:Test", {})
        with self.assertRaises(FileNotFoundError):
            builder.add_name("not_in_use.py:Test", {})


class TestFunctions(unittest.TestCase):
    """test module level functions"""

    def test_hierarchy_from_config(self) -> None:
        """test hierarchy_from_config"""
        config = {
            "resolve": "module",
            "containers": [
                {
                    "name": "pyhp.backends.files.Directory",
                    "config": {
                        "path": "."
                    }
                }
            ]
        }
        with util.hierarchy_from_config(compiler, config) as container:
            self.assertIsInstance(container, CodeSourceContainer)
        del config["resolve"]
        with util.hierarchy_from_config(compiler, config) as container:
            self.assertIsInstance(container, CodeSourceContainer)
        config["resolve"] = "path"
        config["containers"] = [
            {"name": "./tests/backends/dummy.py:HashMap", "config": {}},
        ]
        with util.hierarchy_from_config(compiler, config) as container:
            self.assertIsInstance(container, CodeSourceContainer)
        del config["resolve"]
        config["containers"] = [
            {"name": "tests.backends.test_util.dummy", "config": {}},
            {"name": "broken.name", "config": {}}
        ]
        with self.assertRaises(ImportError):
            util.hierarchy_from_config(compiler, config)
        dummy.close.assert_called_once()
        dummy.close.reset_mock()
        del config["containers"][0]     # test handling of no containers
        with self.assertRaises(ImportError):
            util.hierarchy_from_config(compiler, config)
        with self.assertRaises(ValueError):
            util.hierarchy_from_config(compiler, {"resolve": 42})
