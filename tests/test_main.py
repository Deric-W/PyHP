#!/usr/bin/python3

"""Unit tests for the PyHP cli"""

import sys
import os
import unittest
import subprocess
from tempfile import NamedTemporaryFile
from pyhp import main


class TestCli(unittest.TestCase):
    """Test command line interface"""
    def test_stdin(self) -> None:
        """test reading from stdin"""
        self.assertEqual(
            subprocess.run(         # nosec -> inmutable input
                [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf"],
                input=b"Test",
                check=True,
                stdout=subprocess.PIPE
            ).stdout,
            "Status: 200 OK{0}Content-Type: text/html{0}{0}Test".format(os.linesep).encode()
        )

    def test_empty_config(self) -> None:
        """test empty config file"""
        self.assertEqual(
            subprocess.run(         # nosec -> imutable input
                [sys.executable, "-m", "pyhp", "--config", os.devnull],
                input=b"Test",
                check=True,
                stdout=subprocess.PIPE
            ).stdout,
            "Status: 200 OK{0}Content-Type: text/html{0}{0}Test".format(os.linesep).encode()
        )

    def test_invalid_path(self) -> None:
        """test failure on invalid file path"""
        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.run(         # nosec -> imutable input
                [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "azhdawihd1ihudhai5iwzgbdua"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )


class TestOutput(unittest.TestCase):
    """Test output of example scripts"""
    def test_syntax(self) -> None:
        """test basic pyhp syntax"""
        with open("./tests/embedding/syntax.output", "rb") as fd:
            self.assertEqual(
                subprocess.run(     # nosec -> imutable input
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/embedding/syntax.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/embedding/shebang.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/embedding/indentation.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/header/header.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/header/headers_list.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/header/header_remove.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/header/headers_sent.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/header/header_register_callback.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/cookie/setcookie.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/cookie/setrawcookie.pyhp"],
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
                        [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/request/methods.pyhp"],
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
                        [sys.executable, "-m", "pyhp", "--config", "./tests/request/request-order.conf", "./tests/request/request-order.pyhp"],
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
                    [sys.executable, "-m", "pyhp", "--config", "./pyhp.conf", "./tests/shutdown_functions/register_shutdown_function.pyhp"],
                    check=True,
                    stdout=subprocess.PIPE
                ).stdout,
                fd.read(),
            )


class CheckInternals(unittest.TestCase):
    """check internal functions"""
    def test_check_caching(self) -> None:
        """test the caching detection"""
        self.assertTrue(main.check_if_caching("test", True, True, True))
        self.assertTrue(main.check_if_caching("test", True, True, False))
        self.assertTrue(main.check_if_caching("test", False, True, True))
        self.assertTrue(main.check_if_caching("test", True, True, False))
        self.assertFalse(main.check_if_caching("", True, True, True))
        self.assertFalse(main.check_if_caching("", True, True, False))
        self.assertFalse(main.check_if_caching("", False, True, True))
        self.assertFalse(main.check_if_caching("", True, True, False))
        self.assertFalse(main.check_if_caching("test", True, False, True))
        self.assertFalse(main.check_if_caching("test", True, False, False))
        self.assertFalse(main.check_if_caching("test", False, False, True))
        self.assertFalse(main.check_if_caching("test", False, True, False))

    def test_prepare_file(self) -> None:
        """test the code retrieval"""
        file = NamedTemporaryFile("w+", delete=False)
        try:
            file.write("Test")
            file.close()
            self.assertEqual(main.prepare_file(file.name), "Test")
        finally:
            os.unlink(file.name)

    def test_prepare_file_shebang(self) -> None:
        """test code tetrieval of files with a shebang"""
        file = NamedTemporaryFile("w+", delete=False)
        try:
            file.write("#!Test\nTest\nTest")
            file.close()
            self.assertEqual(main.prepare_file(file.name), "Test\nTest")
        finally:
            os.unlink(file.name)

    def test_import_path(self) -> None:
        """test the importing of files"""
        original_path = sys.path.copy()

        file = NamedTemporaryFile("w", suffix=".py", delete=False)
        try:
            file.write("works = True")
            file.close()
            self.assertTrue(main.import_path(file.name).works)
        finally:
            os.unlink(file.name)

        self.assertEqual(original_path, sys.path)
