#!/usr/bin/python3

"""Tests for pyhp.wsgi.apps"""

from __future__ import annotations
import re
import unittest
import unittest.mock
from typing import Type, Mapping, Any, Generator
from pyhp.wsgi import Environ, StartResponse
from pyhp.wsgi.apps import SimpleWSGIApp
from pyhp.wsgi.interfaces import WSGIInterface, WSGIInterfaceFactory
from pyhp.backends.files import Directory
from pyhp.backends.caches import CacheSourceContainer
from pyhp.compiler.parsers import RegexParser
from pyhp.compiler.generic import GenericCodeBuilder
from pyhp.compiler.util import Compiler


container = Directory(
    "tests",
    Compiler(
        RegexParser(
            re.compile(r"<\?pyhp\s"),
            re.compile(r"\s\?>")
        ),
        GenericCodeBuilder(-1)
    )
)


class DummyFactory(WSGIInterfaceFactory):
    """factory for testing"""

    def __init__(self) -> None:
        self.mock = unittest.mock.Mock(spec=WSGIInterface)
        self.mock.close.configure_mock(side_effect=lambda: print("shutdown"))

    @classmethod
    def from_config(cls: Type[DummyFactory], config: Mapping[str, Any], cache: CacheSourceContainer) -> DummyFactory:
        """create an instance from config data and a cache"""
        return cls()

    def interface(self, environ: Environ, start_response: StartResponse) -> WSGIInterface:
        """create an interface"""
        return self.mock


class BrokenFactory(WSGIInterfaceFactory):
    """factory for testing of broken interfaces"""

    def __init__(self) -> None:
        self.mock = unittest.mock.Mock(spec=WSGIInterface)
        self.mock.end_headers.configure_mock(side_effect=lambda: 1 + "b")   # type: ignore

    @classmethod
    def from_config(cls: Type[DummyFactory], config: Mapping[str, Any], cache: CacheSourceContainer) -> DummyFactory:
        """create an instance from config data and a cache"""
        return cls()

    def interface(self, environ: Environ, start_response: StartResponse) -> WSGIInterface:
        """create an interface"""
        return self.mock


class TestSimpleWSGIApp(unittest.TestCase):
    """test the single threaded implementation"""

    def test_eq(self) -> None:
        """test SimpleWSGIAPP.__eq__"""
        with SimpleWSGIApp(container["embedding/shebang.pyhp"], 1) as app1, \
                SimpleWSGIApp(container["embedding/shebang.pyhp"], 2) as app2, \
                SimpleWSGIApp(container["embedding/syntax.pyhp"], 1) as app3:     # type: ignore
            self.assertEqual(app1, app1)
            self.assertNotEqual(app1, app2)
            self.assertNotEqual(app1, app3)
            self.assertNotEqual(app1, 42)

    def test_protocol(self) -> None:
        """test SimpleWSGIAPP.__call___"""
        start_response = lambda s, h, e: lambda x: None
        factory = DummyFactory()
        interface = factory.mock

        # test output
        with SimpleWSGIApp(container["embedding/shebang.pyhp"], factory) as app:
            output = []
            iterator = iter(app({}, start_response))
            interface.end_headers.assert_not_called()
            output.append(next(iterator))
            interface.end_headers.assert_called()
            interface.end_headers.reset_mock()
            output.extend(iterator)
            self.assertEqual(
                b"".join(output),
                b"\n".join((
                    b"<html>",
                    b"    <head>",
                    b"        <title>Shebang</title>",
                    b"    </head>",
                    b"    <body>",
                    b"        If a Shebang is detected (first line starts with #!) the first line is removed before processing the file\n",
                    b"    </body>",
                    b"</html>",
                    b"shutdown\n"
                ))
            )
            interface.end_headers.assert_not_called()
            interface.close.assert_called()
            interface.close.reset_mock()
            generator = iter(app({}, start_response))   # type: Generator[bytes, None, None]
            next(generator)
            generator.close()   # check if .close is being called but no output is being send
            interface.end_headers.assert_called()
            interface.close.assert_called()

        # test behavior with missing text sections
        interface.end_headers.reset_mock()
        interface.close.reset_mock()
        with SimpleWSGIApp(container["wsgi/empty.pyhp"], factory) as app:
            self.assertEqual(b"".join(app({}, start_response)), b"shutdown\n")
            interface.end_headers.assert_called()
            interface.close.assert_called()

        # test error handling
        interface.end_headers.reset_mock()
        interface.close.reset_mock()
        with SimpleWSGIApp(container["wsgi/error.pyhp"], factory) as app:
            iterator = iter(app({}, start_response))
            self.assertEqual(next(iterator), b"shutdown\n")
            interface.end_headers.assert_called()
            with self.assertRaises(RuntimeError):
                next(iterator)
            interface.close.assert_called()

        # test SystemExit handling
        interface.end_headers.reset_mock()
        interface.close.reset_mock()
        with SimpleWSGIApp(container["wsgi/exit1.pyhp"], factory) as app:
            self.assertEqual(b"".join(app({}, start_response)), b"shutdown\n")
            interface.end_headers.assert_called()
            interface.close.assert_called()
        interface.end_headers.reset_mock()
        interface.close.reset_mock()
        with SimpleWSGIApp(container["wsgi/exit2.pyhp"], factory) as app:
            self.assertEqual(
                b"".join(app({}, start_response)),
                b"\n".join((
                    b"",
                    b"<html>",
                    b"    <head>",
                    b"        <title>Exit</title>",
                    b"    </head>",
                    b"    <body>",
                    b"        <p>Exit test</p>",
                    b"        shutdown\n"
                ))
            )

        # test .end_headers() error handling
        factory = BrokenFactory()
        interface = factory.mock
        with SimpleWSGIApp(container["embedding/syntax.pyhp"], factory) as app:
            with self.assertRaises(TypeError):
                next(iter(app({}, start_response)))
            interface.close.assert_called()
        interface.close.reset_mock()
        with SimpleWSGIApp(container["wsgi/error.pyhp"], factory) as app:
            with self.assertRaises(TypeError):
                next(iter(app({}, start_response)))
            interface.close.assert_called()

    def test_code_source(self) -> None:
        """test SimpleWSGIApp.code_source and cleanup"""
        source = container["embedding/syntax.pyhp"]
        with SimpleWSGIApp(source, None) as app:    # type: ignore
            self.assertEqual(source, app.code_source())
        self.assertTrue(source.fd.closed)
