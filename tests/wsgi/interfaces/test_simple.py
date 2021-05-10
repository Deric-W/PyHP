#!/usr/bin/python3

"""Tests for the simple interface implementation"""

import unittest
from wsgiref.headers import Headers
from typing import Optional, Callable, List, Tuple
from pyhp.wsgi import ExcInfo
from pyhp.wsgi.interfaces.simple import SimpleWSGIInterface, SimpleWSGIInterfaceFactory


class TestSimpleWSGIInterface(unittest.TestCase):
    """tests for SimpleWSGIInterface"""

    def test_eq(self) -> None:
        """test SimpleWSGIInterface.__eq__"""
        start_response = lambda a, b, c: lambda x: None
        interfaces = (
            SimpleWSGIInterface(
                {},
                start_response,
                "200 OK",
                Headers(),
                None
            ),
            SimpleWSGIInterface(
                {"a": 42},
                start_response,
                "200 OK",
                Headers(),
                None
            ),
            SimpleWSGIInterface(
                {},
                lambda a, b, c: None,
                "200 OK",
                Headers(),
                None
            ),
            SimpleWSGIInterface(
                {},
                start_response,
                "400 Bad Request",
                Headers(),
                None
            ),
            SimpleWSGIInterface(
                {},
                start_response,
                "200 OK",
                Headers([("Context-Type", "test/plain")]),
                None
            ),
            SimpleWSGIInterface(
                {},
                start_response,
                "200 OK",
                Headers(),
                42
            )
        )
        for interface in interfaces:
            self.assertEqual([obj for obj in interfaces if obj == interface], [interface])
        self.assertNotEqual(interfaces[0], 42)

    def test_status(self) -> None:
        """test SimpleWSGIInterface.*_status_code"""
        interface = SimpleWSGIInterface(
            {},
            lambda a, b, c: None,
            "200 OK",
            Headers(),
            None
        )
        self.assertEqual(interface.status, "200 OK")
        self.assertEqual(interface.get_status_code(), 200)
        interface.set_status_code(400)
        self.assertEqual(interface.status, "400 Bad Request")
        self.assertEqual(interface.get_status_code(), 400)
        with self.assertRaises(ValueError):
            interface.set_status_code(900)

    def test_end_headers(self) -> None:
        """test SimpleWSGIInterface.end_headers"""
        interface = SimpleWSGIInterface(
            {},
            self.start_response,
            "400 Bad Request",
            Headers(),
            None
        )
        interface.headers.add_header("Content-Type", "text/plain", charset="UTF-8")
        interface.end_headers()

    def start_response(self, status: str, headers: List[Tuple[str, str]], exc_info: Optional[ExcInfo] = None) -> Callable[[bytes], None]:
        """start_response dummy"""
        self.assertEqual(status, "400 Bad Request")
        self.assertEqual(headers, [("Content-Type", 'text/plain; charset="UTF-8"')])
        self.assertIs(exc_info, None)
        return lambda b: None


class TestSimpleWSGIInterfaceFactory(unittest.TestCase):
    """tests for SimpleWSGIInterfaceFactory"""

    def test_eq(self) -> None:
        """test SimpleWSGIInterfaceFactory.__eq__"""
        factories = (
            SimpleWSGIInterfaceFactory("200 OK", [], None),
            SimpleWSGIInterfaceFactory("400 Bad Request", [], None),
            SimpleWSGIInterfaceFactory("200 OK", [("Content-Type", "test/plain")], None)
        )
        for factory in factories:
            self.assertEqual([f for f in factories if f == factory], [factory])
        self.assertNotEqual(factories[0], 42)

    def test_from_config(self) -> None:
        """test SimpleWSGIInterfaceFactory.from_config"""
        with self.assertRaises(ValueError):
            SimpleWSGIInterfaceFactory.from_config({"default_status": []}, None)
        with self.assertRaises(ValueError):
            SimpleWSGIInterfaceFactory.from_config({"default_headers": 42}, None)
        factory = SimpleWSGIInterfaceFactory.from_config({}, None)
        self.assertEqual(factory.default_headers, [("Content-Type", 'text/html; charset="UTF-8"')])
        self.assertEqual(factory.default_status, "200 OK")
        factory = SimpleWSGIInterfaceFactory.from_config(
            {
                "default_status": "400 Bad Request",
                "default_headers": []
            },
            None
        )
        self.assertEqual(factory.default_headers, [])
        self.assertEqual(factory.default_status, "400 Bad Request")

    def test_interface(self) -> None:
        """test SimpleWSGIInterfaceFactory.interface"""
        start_response = lambda a, b, c: lambda d: None
        environ = {"a", 42}
        factory = SimpleWSGIInterfaceFactory("200 OK", [("Content-Type", 'text/html; charset="UTF-8"')], None)
        interface = factory.interface(environ, start_response)
        self.assertEqual(interface.environ, environ)
        self.assertEqual(interface.start_response, start_response)
        self.assertEqual(interface.status, "200 OK")
        self.assertEqual(interface.headers.items(), [("Content-Type", 'text/html; charset="UTF-8"')])
        self.assertIs(interface.cache, None)
