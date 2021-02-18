#!/usr/bin/python3

"""Unit tests for the PyHP cli"""

import sys
import os
import unittest
import subprocess
from tempfile import NamedTemporaryFile
import toml
from pyhp import main


class TestCli(unittest.TestCase):
    """Test command line interface"""
    def test_stdin(self) -> None:
        """test reading from stdin"""
        self.assertEqual(
            subprocess.run(         # nosec -> inmutable input
                [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml"],
                input=b"Test\nTest1",
                check=True,
                stdout=subprocess.PIPE
            ).stdout,
            b"Status: 200 OK\r\nContent-Type: text/html\r\n\r\nTest\nTest1"
        )

    def test_invalid_path(self) -> None:
        """test failure on invalid file path"""
        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.run(         # nosec -> imutable input
                [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "azhdawihd1ihudhai5iwzgbdua"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    def test_stdout(self) -> None:
        """test stdout cleanup"""
        stdout = sys.stdout
        with NamedTemporaryFile("w", dir=".", delete=False) as fd:
            path = fd.name
        try:
            main.main(path, toml.load("pyhp.toml"))
        finally:
            os.unlink(path)
        self.assertIs(sys.stdout, stdout)

    def test_config_location(self) -> None:
        """test config file location"""
        with self.assertRaises(RuntimeError):   # no config
            main.load_config()
        os.environ["PYHPCONFIG"] = "pyhp.toml"  # env var
        try:
            main.load_config()
        finally:
            del os.environ["PYHPCONFIG"]
        self.assertEqual(                       # search path
            main.load_config(("test1", "test2", "pyhp.toml")),
            toml.load("pyhp.toml")
        )


class TestOutput(unittest.TestCase):
    """Test output of example scripts"""
    def test_syntax(self) -> None:
        """test basic pyhp syntax"""
        with open("./tests/embedding/syntax.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/embedding/syntax.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_shebang(self) -> None:
        """test shebang support"""
        with open("./tests/embedding/shebang.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/embedding/shebang.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_indentation(self) -> None:
        """test auto dedent"""
        with open("./tests/embedding/indentation.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/embedding/indentation.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_header(self) -> None:
        """test PyHP.header"""
        with open("./tests/header/header.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/header/header.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_header_list(self) -> None:
        """test PyHP.headers_list"""
        with open("./tests/header/headers_list.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/header/headers_list.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_header_remove(self) -> None:
        """test PyHP.header_remove"""
        with open("./tests/header/header_remove.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/header/header_remove.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_header_sent(self) -> None:
        """test PyHP.headers_sent"""
        with open("./tests/header/headers_sent.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/header/headers_sent.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_header_callbacks(self) -> None:
        """test PyHP.header_register_callback"""
        with open("./tests/header/header_register_callback.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/header/header_register_callback.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_setcookie(self) -> None:
        """test PyHP.setcookie"""
        with open("./tests/cookie/setcookie.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/cookie/setcookie.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_setrawcookie(self) -> None:
        """test PyHP.setrawcookie"""
        with open("./tests/cookie/setrawcookie.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/cookie/setrawcookie.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )

    def test_request_methods(self) -> None:
        """test implemented request methods"""
        os.environ["QUERY_STRING"] = "test0=Hello&Test1=World%21&Test2=&Test3&&test0=World!"
        os.environ["HTTP_COOKIE"] = "test0=Hello ; Test1 = World%21 = Hello; Test2 = ;Test3;;test0=World!; ;"
        try:
            with open("./tests/request/methods.output", "rb") as fd:
                self.assertEqual(
                    subprocess.run(     # nosec -> imutable input
                        [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/request/methods.pyhp"],
                        check=True,
                        stdout=subprocess.PIPE
                    ).stdout,
                    fd.read(),
                )
        finally:
            del os.environ["QUERY_STRING"]
            del os.environ["HTTP_COOKIE"]

    def test_request_order(self) -> None:
        """test alternative request order"""
        os.environ["QUERY_STRING"] = "test0=Hello&Test1=World%21&Test2=&Test3&&test0=World!"
        os.environ["HTTP_COOKIE"] = "test0=Hello ; Test1 = World%21 = Hello; Test2 = ;Test3;;test0=World!; ;"
        try:
            with open("./tests/request/request-order.output", "rb") as fd:
                self.assertEqual(
                    subprocess.run(     # nosec -> imutable input
                        [sys.executable, "-m", "pyhp", "--config", "./tests/request/request-order.toml", "./tests/request/request-order.pyhp"],
                        check=True,
                        stdout=subprocess.PIPE
                    ).stdout,
                    fd.read(),
                )
        finally:
            del os.environ["QUERY_STRING"]
            del os.environ["HTTP_COOKIE"]

    def test_shutdown_functions(self) -> None:
        """test the execution of shutdown functions on shutdown"""
        with open("./tests/shutdown_functions/register_shutdown_function.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.toml", "./tests/shutdown_functions/register_shutdown_function.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )
