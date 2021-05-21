#!/usr/bin/python3

"""Tests for pyhp.wsgi.util"""

import unittest
import unittest.mock
import sys
import re
import toml
from pyhp.wsgi import util
from pyhp.compiler import generic, parsers
from pyhp.compiler.util import Compiler, Dedenter
from pyhp.backends import CodeSourceContainer, memory, files
from pyhp.backends.caches import CacheSourceContainer
from pyhp.backends.caches.timestamped.memory import MemoryCache
from pyhp.wsgi.apps import SimpleWSGIApp, ConcurrentWSGIApp
from pyhp.wsgi.interfaces import simple, php


compiler = Compiler(
    parsers.RegexParser(
        re.compile(r"<\?pyhp\s"),
        re.compile(r"\s\?>")
    ),
    Dedenter(
        generic.GenericCodeBuilder(-1)
    )
)

dummy = unittest.mock.Mock(spec=CodeSourceContainer)
dummy.from_config.configure_mock(side_effect=lambda c, b: dummy)
cache_dummy = unittest.mock.Mock(spec=CacheSourceContainer)
cache_dummy.from_config.configure_mock(side_effect=lambda c, b: cache_dummy)


class BrokenFactory(util.SimpleWSGIAppFactory):
    """factory to test error handling"""

    @staticmethod
    def get_interface_factory(cache, interface_config):
        raise RuntimeError

    @staticmethod
    def get_backend(compiler, backend_config):
        return cache_dummy


class TestFunctions(unittest.TestCase):
    """tests for module level functions"""

    def test_create_backend(self) -> None:
        """test create_backend"""
        config = toml.load("pyhp.toml")["backend"]
        with util.create_backend(compiler, config) as container:
            self.assertIsInstance(container, CodeSourceContainer)
        del config["resolve"]
        with util.create_backend(compiler, config) as container:
            self.assertIsInstance(container, CodeSourceContainer)
        config["containers"] = [
            {"name": "tests.wsgi.test_util.dummy", "config": {}},
            {"name": "broken.name", "config": {}}
        ]
        with self.assertRaises(ImportError):
            util.create_backend(compiler, config)
        dummy.close.assert_called_once()
        dummy.close.reset_mock()
        del config["containers"][0]     # test handling of IndexError
        with self.assertRaises(ImportError):
            util.create_backend(compiler, config)
        with self.assertRaises(ValueError):
            util.create_backend(compiler, {"resolve": 42})

    def test_create_compiler(self) -> None:
        """test create_compiler"""
        self.assertEqual(
            util.create_compiler(compiler.parser, {}),
            compiler
        )
        self.assertIsInstance(
            util.create_compiler(compiler.parser, {"dedent": False}).base_builder,
            generic.GenericCodeBuilder
        )
        with self.assertRaises(ValueError):
            util.create_compiler(compiler.parser, {"optimization_level": "test"})


class TestSimpleWSGIAppFactory(unittest.TestCase):
    """tests for SimpleWSGIAppFactory"""

    def test_app(self) -> None:
        """test SimpleWSGIAppFactory.app"""
        factory = simple.SimpleWSGIInterfaceFactory("200 Ok", [], None)
        with memory.HashMap.from_config({"test": "test"}, compiler) as backend:
            self.assertEqual(
                util.SimpleWSGIAppFactory(
                    factory,
                    compiler,
                    backend,
                    None
                ).app("test"),
                SimpleWSGIApp(backend["test"], factory)
            )

    def test_eq(self) -> None:
        """test SimpleWSGIAppFactory.__eq__"""
        factory1 = simple.SimpleWSGIInterfaceFactory("200 Ok", [], None)
        factory2 = simple.SimpleWSGIInterfaceFactory("200 Ok", [("a", "b")], None)
        with memory.HashMap.from_config({"test": "test"}, compiler) as backend:
            factories = [
                util.SimpleWSGIAppFactory(factory1, compiler, backend, None),
                util.SimpleWSGIAppFactory(factory2, compiler, backend, None),
                util.SimpleWSGIAppFactory(factory1, None, backend, None),
                util.SimpleWSGIAppFactory(factory1, compiler, None, None)
            ]
            for factory in factories:
                self.assertEqual([obj for obj in factories if obj == factory], [factory])
            self.assertNotEqual(factories[0], 42)

    def test_from_config(self) -> None:
        """test SimpleWSGIAppFactory.from_config"""
        config = {"backend": {"containers": [{"name": "pyhp.backends.files.Directory", "config": {"path": "."}}]}}
        with files.Directory(".", compiler) as backend:
            with util.SimpleWSGIAppFactory.from_config(config) as factory:
                self.assertEqual(
                    util.SimpleWSGIAppFactory(
                        php.PHPWSGIInterfaceFactory.from_config({}, None),
                        compiler,
                        backend,
                        None
                    ),
                    factory
                )
            config["backend"]["containers"].append(
                {"name": "pyhp.backends.caches.timestamped.memory.MemoryCache", "config": {}}
            )
            with util.SimpleWSGIAppFactory.from_config(config) as factory:
                cache = MemoryCache.from_config({}, backend)
                self.assertEqual(
                    util.SimpleWSGIAppFactory(
                        php.PHPWSGIInterfaceFactory.from_config({}, cache),
                        compiler,
                        cache,
                        cache
                    ),
                    factory
                )
        with self.assertRaises(RuntimeError):
            BrokenFactory.from_config({})
        cache_dummy.close.assert_called_once()
        cache_dummy.close.reset_mock()

    def test_from_config_file(self) -> None:
        """test SimpleWSGIAppFactory.from_config_file"""
        config = toml.load("pyhp.toml")
        with open("pyhp.toml", "r") as file:
            self.assertEqual(
                util.SimpleWSGIAppFactory.from_config(config),
                util.SimpleWSGIAppFactory.from_config_file(file)
            )

    def test_get_interface_factory(self) -> None:
        """test SimpleWSGIAppFactory.get_interface_factory"""
        self.assertEqual(
            util.SimpleWSGIAppFactory.get_interface_factory(None, {}),
            php.PHPWSGIInterfaceFactory.from_config({}, None)
        )
        self.assertEqual(
            util.SimpleWSGIAppFactory.get_interface_factory(None, {"name": "php", "config": {"default_status": 400}}),
            php.PHPWSGIInterfaceFactory.from_config({"default_status": 400}, None)
        )
        self.assertEqual(
            util.SimpleWSGIAppFactory.get_interface_factory(None, {"name": "simple", "config": {"default_status": "400 Bad Request"}}),
            simple.SimpleWSGIInterfaceFactory.from_config({"default_status": "400 Bad Request"}, None)
        )
        with self.assertRaises(ValueError):
            util.SimpleWSGIAppFactory.get_interface_factory(None, {"name": "oshadashdiauhd"})

    def test_close(self) -> None:
        """test SimpleWSGIAppFactory.close"""
        dummy1 = unittest.mock.Mock(spec=CodeSourceContainer)
        dummy1.from_config.configure_mock(side_effect=lambda c, b: dummy1)
        dummy2 = unittest.mock.Mock(spec=CacheSourceContainer)
        dummy2.from_config.configure_mock(side_effect=lambda c, b: dummy2)
        dummy3 = unittest.mock.Mock(spec=CacheSourceContainer)
        dummy3.from_config.configure_mock(side_effect=lambda c, b: dummy3)
        dummy3.close.configure_mock(side_effect=RuntimeError)
        util.SimpleWSGIAppFactory(None, None, dummy1, dummy2).close()
        dummy1.close.assert_called_once()
        dummy2.close.assert_called_once()
        dummy1.close.reset_mock()
        dummy2.close.reset_mock()
        util.SimpleWSGIAppFactory(None, None, dummy1, dummy1).close()
        dummy1.close.assert_called_once()
        dummy1.close.reset_mock()
        util.SimpleWSGIAppFactory(None, None, dummy1, None).close()
        dummy1.close.assert_called_once()
        dummy1.close.reset_mock()
        with self.assertRaises(RuntimeError):
            util.SimpleWSGIAppFactory(None, None, dummy1, dummy3).close()
        dummy1.close.assert_called_once()
        dummy3.close.assert_called_once()


class TestConcurrentWSGIAppFactory(unittest.TestCase):
    """tests for ConcurrentWSGIAppFactory"""

    def test_eq(self) -> None:
        """test ConcurrentWSGIAppFactory.__eq__"""
        factory1 = simple.SimpleWSGIInterfaceFactory("200 Ok", [], None)
        factory2 = simple.SimpleWSGIInterfaceFactory("200 Ok", [("a", "b")], None)
        with memory.HashMap.from_config({"test": "test"}, compiler) as backend:
            try:
                app_factory = util.ConcurrentWSGIAppFactory(factory1, compiler, backend, None)
                self.assertNotEqual(    # different sys.stdout default
                    app_factory,
                    util.ConcurrentWSGIAppFactory(factory1, compiler, backend, None)
                )
                sys.stdout = sys.__stdout__
                self.assertEqual(
                    app_factory,
                    util.ConcurrentWSGIAppFactory(factory1, compiler, backend, None)
                )
                sys.stdout = sys.__stdout__
                self.assertNotEqual(
                    app_factory,
                    util.ConcurrentWSGIAppFactory(factory2, compiler, backend, None)
                )
                sys.stdout = sys.__stdout__
                self.assertNotEqual(
                    app_factory,
                    util.ConcurrentWSGIAppFactory(factory1, None, backend, None)
                )
                sys.stdout = sys.__stdout__
                self.assertNotEqual(
                    app_factory,
                    util.ConcurrentWSGIAppFactory(factory1, compiler, None, None)
                )
                self.assertNotEqual(app_factory, 42)
            finally:
                sys.stdout = sys.__stdout__

    def test_close(self) -> None:
        """test ConcurrentWSGIAppFactory.close"""
        try:
            dummy1 = unittest.mock.Mock(spec=CodeSourceContainer)
            dummy1.from_config.configure_mock(side_effect=lambda c, b: dummy1)
            dummy2 = unittest.mock.Mock(spec=CacheSourceContainer)
            dummy2.from_config.configure_mock(side_effect=lambda c, b: dummy2)
            dummy3 = unittest.mock.Mock(spec=CacheSourceContainer)
            dummy3.from_config.configure_mock(side_effect=lambda c, b: dummy3)
            dummy3.close.configure_mock(side_effect=RuntimeError)
            util.ConcurrentWSGIAppFactory(None, None, dummy1, dummy2).close()
            dummy1.close.assert_called_once()
            dummy2.close.assert_called_once()
            dummy1.close.reset_mock()
            dummy2.close.reset_mock()
            util.ConcurrentWSGIAppFactory(None, None, dummy1, dummy1).close()
            dummy1.close.assert_called_once()
            dummy1.close.reset_mock()
            util.ConcurrentWSGIAppFactory(None, None, dummy1, None).close()
            dummy1.close.assert_called_once()
            dummy1.close.reset_mock()
            with self.assertRaises(RuntimeError):
                util.ConcurrentWSGIAppFactory(None, None, dummy1, dummy3).close()
            dummy1.close.assert_called_once()
            dummy3.close.assert_called_once()
            self.assertIs(sys.stdout, sys.__stdout__)
        finally:
            sys.stdout = sys.__stdout__

    def test_app(self) -> None:
        """test ConcurrentWSGIAppFactory.app"""
        factory = simple.SimpleWSGIInterfaceFactory("200 Ok", [], None)
        with memory.HashMap.from_config({"test": "test"}, compiler) as backend, \
                util.ConcurrentWSGIAppFactory(factory, compiler, backend, None) as app_factory:
            self.assertEqual(
                app_factory.app("test"),
                ConcurrentWSGIApp("test", backend, app_factory.proxy, factory)
            )
