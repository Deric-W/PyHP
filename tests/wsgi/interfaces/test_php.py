#!/usr/bin/python3

"""tests for pyhp.wsgi.interfaces.php"""

import sys
import os
import unittest
import unittest.mock
import time
from tempfile import TemporaryDirectory, gettempdir
from wsgiref.headers import Headers
from pyhp.wsgi.interfaces import php
from pyhp.wsgi.interfaces.phputils import NullStreamFactory, UploadStreamFactory, UploadError


class TestFunctions(unittest.TestCase):
    """tests for stand-alone functions"""

    def test_close_files(self) -> None:
        """test close_files"""
        files = [
            unittest.mock.Mock(),
            unittest.mock.Mock(),
            unittest.mock.Mock(),
            unittest.mock.Mock()
        ]
        files[1].close.configure_mock(side_effect=RuntimeError)
        files[2].close.configure_mock(side_effect=ValueError)
        try:
            php.close_files(files)
        except ValueError as e:
            self.assertIsInstance(e.__context__, RuntimeError)
        for mock in files:
            mock.close.assert_called()
        files.clear()
        php.close_files(files)


class TestPHPWSGIInterface(unittest.TestCase):
    """tests for PHPWSGIInterface"""

    def test_eq(self) -> None:
        """test PHPWSGIInterface.__eq__"""
        start_response = lambda s, h, e: lambda b: None
        interface = php.PHPWSGIInterface({}, start_response, 200, Headers(), None)
        self.assertEqual(
            interface,
            interface
        )
        self.assertNotEqual(
            interface,
            php.PHPWSGIInterface({}, start_response, 400, Headers(), None)
        )
        self.assertNotEqual(
            interface,
            php.PHPWSGIInterface({}, start_response, 200, Headers([("a", "b")]), None)
        )
        self.assertNotEqual(
            interface,
            42
        )

    def test_server(self) -> None:
        """test PHPWSGIInterface.SERVER"""
        environ = {
            "PATH_INFO": "/test",
            "SCRIPT_NAME": "/test.pyhp",
            "HTTP_AUTHORIZATION": "Basic YWxhZGRpbjpvcGVuc2VzYW1l",
            "QUERY_STRING": "a=b",
            "CUSTOM": "test"
        }
        timestamp = time.time()
        with php.PHPWSGIInterface(environ, lambda s, h, e: lambda b: None, 200, Headers(), None) as interface:
            self.assertEqual(interface.SERVER["argv"], "a=b")
            self.assertEqual(interface.SERVER["PHP_SELF"], "/test.pyhp/test")
            self.assertEqual(interface.SERVER["PHP_AUTH_USER"], "aladdin")
            self.assertEqual(interface.SERVER["AUTH_TYPE"], "basic")
            self.assertEqual(interface.SERVER["PHP_AUTH_PW"], "opensesame")
            self.assertNotIn("PHP_AUTH_DIGEST", interface.SERVER)
            self.assertEqual(int(interface.SERVER["REQUEST_TIME_FLOAT"]), interface.SERVER["REQUEST_TIME"])
            self.assertTrue(timestamp <= interface.SERVER["REQUEST_TIME_FLOAT"] <= time.time())
            self.assertIn("CUSTOM", interface.SERVER)

    def test_get(self) -> None:
        """test PHPWSGIInterface.GET"""
        environ = {
            "QUERY_STRING": "a=b&a=c&b=&c&x=%C3%A4"
        }
        with php.PHPWSGIInterface(environ, lambda s, h, e: lambda b: None, 200, Headers(), None) as interface:
            self.assertEqual(
                list(interface.GET.items(multi=True)),
                [("a", "b"), ("a", "c"), ("b", ""), ("c", ""), ("x", "ä")]
            )
        with php.PHPWSGIInterface({}, lambda s, h, e: lambda b: None, 200, Headers(), None) as interface:
            self.assertEqual(len(interface.GET), 0)

    def test_cookie(self) -> None:
        """test PHPWSGIInterface.COOKIE"""
        environ = {
            "HTTP_COOKIE": 'a="b"; a=c; a=; b; c=%C3%A4'
        }
        with php.PHPWSGIInterface(environ, lambda s, h, e: lambda b: None, 200, Headers(), None) as interface:
            self.assertEqual(
                list(interface.COOKIE.items(multi=True)),
                [("a", "b"), ("a", "c"), ("a", ""), ("b", ""), ("c", "ä")]
            )
        with php.PHPWSGIInterface({}, lambda s, h, e: lambda b: None, 200, Headers(), None) as interface:
            self.assertEqual(len(interface.COOKIE), 0)

    def test_post(self) -> None:
        """test PHPWSGIInterface.POST"""
        with TemporaryDirectory() as directory, \
                open("tests/wsgi/interfaces/wsgi.input", "rb") as input:
            with php.PHPWSGIInterface(
                    {
                        "REQUEST_METHOD": "POST",
                        "wsgi.input": input,
                        "CONTENT_TYPE": 'multipart/form-data;boundary="boundary"',
                        "CONTENT_LENGTH": "324"
                    },
                    lambda s, h, e: lambda b: None,
                    200,
                    Headers(),
                    None,
                    stream_factory=UploadStreamFactory(directory, 1)
            ) as interface:
                self.assertEqual(
                    list(interface.POST.items(multi=True)),
                    [("field1", "value1"), ("field1", "value1.5")]
                )
                self.assertEqual(len(interface.FILES), 2)
                self.assertEqual(interface.FILES["field2"].name, "example1.txt")
                self.assertEqual(interface.FILES["field2"].error, 0)
                self.assertTrue(interface.FILES["field2"].tmp_name.startswith(directory))
                with open(interface.FILES["field2"].tmp_name, "r") as file:
                    self.assertEqual(file.read(), "value2")
                self.assertEqual(interface.FILES["field3"].error, UploadError.MAX_FILES.value)
            self.assertEqual(len(os.listdir(directory)), 0)

    def test_disabled_post(self) -> None:
        """test disabled POST"""
        with open("tests/wsgi/interfaces/wsgi.input", "rb") as input:
            with php.PHPWSGIInterface(
                    {
                        "REQUEST_METHOD": "POST",
                        "wsgi.input": input,
                        "CONTENT_TYPE": 'multipart/form-data;boundary="boundary"',
                        "CONTENT_LENGTH": "324"
                    },
                    lambda s, h, e: lambda b: None,
                    200,
                    Headers(),
                    None,
                    stream_factory=None
            ) as interface:
                self.assertEqual(len(interface.POST), 0)
                self.assertEqual(len(interface.FILES), 0)
                self.assertEqual(input.tell(), 0)

    def test_post_max_size(self) -> None:
        """test post max size"""
        with open("tests/wsgi/interfaces/wsgi.input", "rb") as input:
            with php.PHPWSGIInterface(
                    {
                        "REQUEST_METHOD": "POST",
                        "wsgi.input": input,
                        "CONTENT_TYPE": 'multipart/form-data;boundary="boundary"',
                        "CONTENT_LENGTH": "324"
                    },
                    lambda s, h, e: lambda b: None,
                    200,
                    Headers(),
                    None,
                    post_max_size=100,
                    stream_factory=NullStreamFactory()
            ) as interface:
                self.assertEqual(len(interface.POST), 0)
                self.assertEqual(len(interface.FILES), 0)

    def test_request(self) -> None:
        """test PHPWSGIInterface.REQUEST"""
        with TemporaryDirectory() as directory, \
                open("tests/wsgi/interfaces/wsgi.input", "rb") as input:
            with php.PHPWSGIInterface(
                    {
                        "REQUEST_METHOD": "POST",
                        "wsgi.input": input,
                        "CONTENT_TYPE": 'multipart/form-data;boundary="boundary"',
                        "CONTENT_LENGTH": "324",
                        "QUERY_STRING": "field1=test&a=b&b=c",
                        "HTTP_COOKIE": "b=d; d=d"
                    },
                    lambda s, h, e: lambda b: None,
                    200,
                    Headers(),
                    None,
                    request_order=("GET", "POST", "unknown", "COOKIE"),
                    stream_factory=UploadStreamFactory(directory, 1)
            ) as interface:
                self.assertEqual(len(interface.REQUEST), 4)
                self.assertEqual(interface.REQUEST.getlist("field1"), ["value1", "value1.5"])
                self.assertEqual(interface.REQUEST["a"], "b")
                self.assertEqual(interface.REQUEST["b"], "d")
                self.assertEqual(interface.REQUEST["d"], "d")

    def test_header(self) -> None:
        """test PHPWSGIInterface.header"""
        with php.PHPWSGIInterface({}, lambda s, h, e: lambda b: None, 200, Headers(), None) as interface:
            interface.header("test: true")
            self.assertEqual(interface.headers.get_all("test"), ["true"])
            interface.header("test: maybe")
            self.assertEqual(interface.headers.get_all("test"), ["maybe"])
            interface.header("test: true", replace=False)
            self.assertEqual(interface.headers.get_all("test"), ["maybe", "true"])
            interface.header("test: false", response_code=400)
            self.assertEqual(interface.headers.get_all("test"), ["false"])
            self.assertEqual(interface.status_code, 400)
            interface.header("Location: test")
            self.assertEqual(interface.status_code, 302)
            interface.header("Location: test", response_code=308)
            self.assertEqual(interface.status_code, 308)
            interface.header("Location: test")
            self.assertEqual(interface.status_code, 308)
            with self.assertRaises(ValueError):
                interface.header("Attack: Injection\r\nPayload: test")
            with self.assertRaises(ValueError):
                interface.header("Attack: Injection\nPayload: test")

    def test_header_remove(self) -> None:
        """test PHPWSGIInterface.header_remove"""
        with php.PHPWSGIInterface({}, lambda s, h, e: lambda b: None, 200, Headers(), None) as interface:
            interface.header("test: true")
            interface.header("test: maybe", replace=False)
            interface.header("a: b")
            interface.header_remove("Test")
            self.assertEqual(interface.headers.items(), [("a", "b")])
            interface.header_remove()
            self.assertEqual(interface.headers.items(), [])

    def tests_headers_list(self) -> None:
        """test PHPWSGIInterface.headers_list"""
        with php.PHPWSGIInterface({}, lambda s, h, e: lambda b: None, 200, Headers(), None) as interface:
            interface.header("test:true")
            interface.header("test: maybe", replace=False)
            interface.header("a: b")
            self.assertEqual(
                interface.headers_list(),
                ["test: true", "test: maybe", "a: b"]
            )

    def test_headers_sent(self) -> None:
        """test PHPWSGIInterface.headers_sent"""
        with php.PHPWSGIInterface({}, lambda s, h, e=None: lambda b: None, 200, Headers(), None) as interface:
            self.assertFalse(interface.headers_sent())
            interface.end_headers()
            self.assertTrue(interface.headers_sent())

    def test_header_register_callback(self) -> None:
        """test PHPWSGIInterface.header_register_callback"""
        with php.PHPWSGIInterface({}, lambda s, h, e=None: lambda b: None, 200, Headers(), None) as interface:
            tests = []
            self.assertTrue(interface.header_register_callback(lambda: tests.append(1)))
            interface.header_register_callback(lambda: tests.append(2))
            interface.end_headers()
            self.assertEqual(tests, [2])
            self.assertFalse(interface.header_register_callback(lambda: tests.append(1)))
        with php.PHPWSGIInterface({}, lambda s, h, e=None: lambda b: None, 200, Headers(), None) as interface:
            tests = []
            interface.header_register_callback(lambda: tests.append(1))
            interface.header_register_callback(lambda: tests.append(2), replace=False)
            interface.end_headers()
            self.assertEqual(tests, [1, 2])

    def test_setcookie(self) -> None:
        """test PHPWSGIInterface.setcookie"""
        with php.PHPWSGIInterface({}, lambda s, h, e=None: lambda b: None, 200, Headers(), None) as interface:
            self.assertTrue(interface.setcookie("a", "b"))
            interface.setcookie("a", "ä")
            interface.setcookie(
                "a",
                "b",
                42,
                "/tests",
                "thetwins.xyz",
                True,
                True,
                "Lax"
            )
            self.assertEqual(
                interface.headers.items(),
                [
                    ("Set-Cookie", 'a="b"'),
                    ("Set-Cookie", 'a="%C3%A4"'),
                    ("Set-Cookie", f'a="b"; Expires=Thu, 01 Jan 1970 00:00:42 GMT; Max-Age={int(42 - time.time())}; Path=/tests; Domain=thetwins.xyz; Secure; HttpOnly; SameSite=Lax')
                ]
            )
            interface.end_headers()
            self.assertFalse(interface.setcookie("a", "b"))

    def test_setrawcookie(self) -> None:
        """test PHPWSGIInterface.setrawcookie"""
        with php.PHPWSGIInterface({}, lambda s, h, e=None: lambda b: None, 200, Headers(), None) as interface:
            self.assertTrue(interface.setrawcookie("a", "b"))
            interface.setrawcookie("a", "ä")
            interface.setrawcookie(
                "a",
                "b",
                42,
                "/tests",
                "thetwins.xyz",
                True,
                True,
                "Lax"
            )
            self.assertEqual(
                interface.headers.items(),
                [
                    ("Set-Cookie", 'a=b'),
                    ("Set-Cookie", 'a=ä'),
                    ("Set-Cookie", f'a=b; Expires=Thu, 01 Jan 1970 00:00:42 GMT; Max-Age={int(42 - time.time())}; Path=/tests; Domain=thetwins.xyz; Secure; HttpOnly; SameSite=Lax')
                ]
            )
            interface.end_headers()
            self.assertFalse(interface.setrawcookie("a", "b"))

    def test_http_response_code(self) -> None:
        """test PHPWSGIInterface.http_response_code"""
        status = []
        with php.PHPWSGIInterface({}, lambda s, h, e=None: status.append(s), 200, Headers(), None) as interface:
            self.assertEqual(interface.http_response_code(400), 200)
            self.assertEqual(interface.http_response_code(), 400)
            interface.end_headers()
            self.assertEqual(status, ["400 Bad Request"])

    def test_register_shutdown_function(self) -> None:
        """test PHPWSGIInterface.register_shutdown_function"""
        tests = []
        with php.PHPWSGIInterface({}, lambda s, h, e=None: lambda b: None, 200, Headers(), None) as interface:
            interface.register_shutdown_function(lambda: tests.append(1))
            interface.register_shutdown_function(lambda x: tests.append(x), 2)
            interface.register_shutdown_function(lambda x=1: tests.append(x), x=3)
            interface.register_shutdown_function(lambda: sys.exit())
            interface.register_shutdown_function(lambda: tests.append(4))
        self.assertEqual(tests, [1, 2, 3])


class TestPHPWSGIInterfaceFactory(unittest.TestCase):
    """tests for PHPWSGIInterfaceFactory"""

    def test_eq(self) -> None:
        """test PHPWSGIInterfaceFactory.__eq__"""
        factories = [
            php.PHPWSGIInterfaceFactory(200, [], None, ("GET", "POST", "COOKIE"), None, None),
            php.PHPWSGIInterfaceFactory(400, [], None, ("GET", "POST", "COOKIE"), None, None),
            php.PHPWSGIInterfaceFactory(200, [("a", "b")], None, ("GET", "POST", "COOKIE"), None, None),
            php.PHPWSGIInterfaceFactory(200, [], None, ("POST", "COOKIE"), None, None),
            php.PHPWSGIInterfaceFactory(200, [], None, ("GET", "POST", "COOKIE"), 5000, None),
            php.PHPWSGIInterfaceFactory(200, [], None, ("GET", "POST", "COOKIE"), None, NullStreamFactory()),
            42
        ]
        for factory in factories:
            self.assertEqual([obj for obj in factories if obj == factory], [factory])

    def test_parse_post_config(self) -> None:
        """test PHPWSGIInterfaceFactory.parse_post_config"""
        self.assertEqual(
            php.PHPWSGIInterfaceFactory.parse_post_config({}),
            (None, UploadStreamFactory(gettempdir(), None))
        )
        self.assertEqual(
            php.PHPWSGIInterfaceFactory.parse_post_config({"enable": False}),
            (None, None)
        )
        self.assertEqual(
            php.PHPWSGIInterfaceFactory.parse_post_config({"uploads": {"enable": False}}),
            (None, NullStreamFactory())
        )
        self.assertEqual(
            php.PHPWSGIInterfaceFactory.parse_post_config({
                "max_size": 42,
                "uploads": {
                    "directory": "/test",
                    "max_files": 20
                }
            }),
            (42, UploadStreamFactory("/test", 20))
        )
        with self.assertRaises(ValueError):
            php.PHPWSGIInterfaceFactory.parse_post_config({"max_size": 9.9})
        with self.assertRaises(ValueError):
            php.PHPWSGIInterfaceFactory.parse_post_config({"uploads": {"max_files": 9.9}})
        with self.assertRaises(ValueError):
            php.PHPWSGIInterfaceFactory.parse_post_config({"uploads": {"directory": 42}})

    def test_from_config(self) -> None:
        """test PHPWSGIInterfaceFactory.from_config"""
        self.assertEqual(
            php.PHPWSGIInterfaceFactory.from_config(
                {
                    "default_status": 400,
                    "default_headers": {
                        "a": ["a", "b"]
                    },
                    "request_order": ["a", "b", "c"]
                },
                None
            ),
            php.PHPWSGIInterfaceFactory(
                400,
                [("a", "a"), ("a", "b")],
                None,
                ["a", "b", "c"],
                None,
                UploadStreamFactory(gettempdir())
            )
        )
        self.assertEqual(
            php.PHPWSGIInterfaceFactory.from_config({}, None),
            php.PHPWSGIInterfaceFactory(
                200,
                [("Content-Type", 'text/html; charset="UTF-8"')],
                None,
                ("GET", "POST", "COOKIE"),
                None,
                UploadStreamFactory(gettempdir())
            )
        )
        with self.assertRaises(ValueError):
            php.PHPWSGIInterfaceFactory.from_config({"default_status": "test"}, None)
        with self.assertRaises(ValueError):
            php.PHPWSGIInterfaceFactory.from_config({"default_headers": 42}, None)
        with self.assertRaises(ValueError):
            php.PHPWSGIInterfaceFactory.from_config({"default_headers": {"a": 42}}, None)
        with self.assertRaises(ValueError):
            php.PHPWSGIInterfaceFactory.from_config({"default_headers": {"a": [42]}}, None)
        with self.assertRaises(ValueError):
            php.PHPWSGIInterfaceFactory.from_config({"request_order": 42}, None)

    def test_interface(self) -> None:
        """test PHPWSGIInterfaceFactory.interface"""
        stream_factory = NullStreamFactory()
        start_response = lambda s, h, e=None: lambda b: None
        environ = {"wsgi.input": sys.stdin}
        with php.PHPWSGIInterfaceFactory(
            400,
            [("a", "b")],
            None,
            ("a", "b", "c"),
            -9,
            stream_factory
        ).interface(environ, start_response) as interface:
            self.assertEqual(interface.environ, environ)
            self.assertIs(interface.start_response, start_response)
            self.assertEqual(interface.status_code, 400)
            self.assertEqual(interface.headers.items(), [("a", "b")])
