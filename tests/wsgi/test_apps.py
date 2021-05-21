#!/usr/bin/python3

"""Tests for pyhp.wsgi.apps"""

from __future__ import annotations
import re
import gc
import unittest
import unittest.mock
import threading
import weakref
import warnings
from io import StringIO
from typing import Type, Mapping, Any, Generator
from pyhp.wsgi import Environ, StartResponse
from pyhp.wsgi.apps import SimpleWSGIApp, ConcurrentWSGIApp
from pyhp.wsgi.proxys import LocalStackProxy
from pyhp.wsgi.interfaces import WSGIInterface, WSGIInterfaceFactory, simple
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


def test_app(app, amount) -> None:
    for _ in range(amount):
        iterator = app({}, lambda s, h, e=None: lambda b: None)
        list(iterator)
        iterator.close()


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
    def from_config(cls: Type[BrokenFactory], config: Mapping[str, Any], cache: CacheSourceContainer) -> BrokenFactory:
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


class TestConcurrentWSGIApp(unittest.TestCase):
    """test ConcurrentWSGIApp"""

    def test_eq(self) -> None:
        """test ConcurrentWSGIApp.__eq__"""
        proxy1 = LocalStackProxy(None)
        proxy2 = LocalStackProxy(42)
        factory1 = DummyFactory()
        factory2 = BrokenFactory()
        apps = [
            ConcurrentWSGIApp("abc", container, proxy1, factory1),
            ConcurrentWSGIApp("def", container, proxy1, factory1),
            ConcurrentWSGIApp("abc", None, proxy1, factory1),
            ConcurrentWSGIApp("abc", container, proxy2, factory1),
            ConcurrentWSGIApp("abc", container, proxy1, factory2)
        ]
        try:
            for app in apps:
                self.assertEqual([obj for obj in apps if obj == app], [app])
            self.assertNotEqual(apps[0], 42)
        finally:
            for app in apps:
                app.close()

    def test_code_source(self) -> None:
        """test ConcurrentWSGIApp.code_source"""
        with ConcurrentWSGIApp(
            "wsgi/empty.pyhp",
            unittest.mock.MagicMock(wraps=container),
            LocalStackProxy(None),
            simple.SimpleWSGIInterfaceFactory("200 OK", [], None)
        ) as app:
            app.backend.__getitem__.configure_mock(side_effect=lambda n: container[n])
            thread1 = threading.Thread(target=lambda: test_app(app, 2))
            thread2 = threading.Thread(target=lambda: test_app(app, 1))
            # coverage semms to keep threads alive with --timid or on PyPy
            # if this is the case skip the second assert and print a warning
            thread1_weakref = weakref.ref(thread1)
            thread1.start()
            thread1.join()
            self.assertEqual(len(app.sources), 1)
            del thread1
            gc.collect()    # make sure thread1 is removed
            thread2.start()
            thread2.join()
            if thread1_weakref() is None:
                self.assertEqual(len(app.sources), 1)
                self.assertEqual(
                    app.backend.__getitem__.mock_calls,
                    [
                        unittest.mock.call("wsgi/empty.pyhp"),
                        unittest.mock.call("wsgi/empty.pyhp")
                    ]
                )
            else:
                warnings.warn("thread1 is somehow being kept alive, probably by coverage tools")

    def test_redirect_stdout(self) -> None:
        """test ConcurrentWSGIApp.redirect_stdout"""
        with ConcurrentWSGIApp("abc", container, LocalStackProxy(None), DummyFactory()) as app:
            buffer = StringIO()
            with app.redirect_stdout(buffer) as buffer2:
                self.assertIs(buffer, buffer2)
                app.proxy.write("test")
            self.assertEqual(buffer.getvalue(), "test")

    def test_close(self) -> None:
        """test ConcurrentWSGIApp.close"""
        app = ConcurrentWSGIApp("abc", container, LocalStackProxy(None), DummyFactory())
        self.assertEqual(len(app.sources), 0)
        sources = {
            0: (unittest.mock.Mock(), None),
            1: (unittest.mock.Mock(), None),
            2: (unittest.mock.Mock(), None)
        }
        sources[1][0].close.configure_mock(side_effect=RuntimeError)
        app.sources.update(sources)
        app.pending_removals.append(9)
        with self.assertRaises(RuntimeError):
            app.close()
        self.assertEqual(len(app.sources), 0)
        self.assertEqual(len(app.pending_removals), 0)
        for source in sources.values():
            source[0].close.assert_called_once()
