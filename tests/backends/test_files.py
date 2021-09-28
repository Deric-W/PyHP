#!/usr/bin/python3

"""Tests for pyhp.backends.files"""

import unittest
import sys
import re
import io
import os
import os.path
import inspect
import importlib.util
import importlib.machinery
from pyhp.backends import SourceInfo
from pyhp.backends.files import (
    FileSource,
    Directory,
    SourceFileLoader,
    LeavesDirectoryError,
    StrictDirectory
)
from pyhp.compiler.parsers import RegexParser
from pyhp.compiler.generic import GenericCodeBuilder
from pyhp.compiler.util import Compiler, Dedenter


compiler = Compiler(
    RegexParser(
        re.compile(r"<\?pyhp\s"),
        re.compile(r"\s\?>")
    ),
    Dedenter(
        GenericCodeBuilder(-1)
    )
)

compiler2 = Compiler(
    RegexParser(
        re.compile(r"<\?pyhp\s"),
        re.compile(r"\s\?>")
    ),
    GenericCodeBuilder(0)   # different than compiler!
)


class TestFileSource(unittest.TestCase):
    """test FileSource"""
    def test_eq(self) -> None:
        """test FileSource.__eq__"""
        sources = [
            FileSource.from_path("tests/embedding/shebang.pyhp", compiler),
            FileSource.from_path("tests/embedding/syntax.pyhp", compiler),
            FileSource.from_path("tests/embedding/syntax.pyhp", compiler2)
        ]
        try:
            for source in sources:
                self.assertEqual(
                    [source],
                    [s for s in sources if s == source]
                )
            self.assertNotEqual(sources[0], 42)
        finally:
            for source in sources:
                source.close()

    def test_with_inferred_spec(self) -> None:
        """test FileSource.with_inferred_spec"""
        with FileSource.with_inferred_spec(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler) as source:
            spec = source.spec
        self.assertEqual(spec.name, "__main__")
        self.assertIsInstance(spec.loader, SourceFileLoader)
        self.assertEqual(spec.origin, "tests/embedding/syntax.pyhp")
        self.assertTrue(spec.has_location)
        with FileSource.with_inferred_spec(io.FileIO(sys.stdin.fileno(), "r", closefd=False), compiler) as source:
            spec = source.spec
        self.assertEqual(spec.name, "__main__")
        self.assertTrue(spec.origin.startswith("<"))
        self.assertFalse(spec.has_location)

    def test_from_path(self) -> None:
        """test FileSource.from_path"""
        with FileSource.from_path("tests/embedding/syntax.pyhp", compiler) as source:
            spec = source.spec
            stat = os.fstat(source.fd.fileno())
        self.assertEqual((stat.st_ino, stat.st_dev), os.stat("tests/embedding/syntax.pyhp")[1:3])
        self.assertEqual(spec.name, "__main__")
        self.assertIsInstance(spec.loader, SourceFileLoader)
        self.assertEqual(spec.origin, "tests/embedding/syntax.pyhp")
        self.assertTrue(spec.has_location)

    def test_code(self) -> None:
        """test FileSource.code"""
        with open("tests/embedding/syntax.pyhp", "r", newline="") as fd, \
                FileSource.from_path("tests/embedding/syntax.pyhp", compiler) as source:
            loader = SourceFileLoader("__main__", "tests/embedding/syntax.pyhp")
            code = compiler.compile_file(fd, loader)
            code2 = source.code()
            code3 = source.code()   # check if source can be read multiple times
            self.assertEqual(code, code2)
            self.assertEqual(code2, code3)

    def test_source(self) -> None:
        """test FileSource.source"""
        with open("tests/embedding/syntax.pyhp", "r") as fd, \
                FileSource.from_path("tests/embedding/syntax.pyhp", compiler) as source:
            # workaround git automatic newlines
            self.assertEqual(fd.read(), source.source().replace(os.linesep, "\n"))

    def test_size(self) -> None:
        """test FileSource.size"""
        with FileSource.from_path("tests/embedding/syntax.pyhp", compiler) as source:
            self.assertEqual(source.size(), len(source.source()))

    def test_introspection(self) -> None:
        """test code introspection"""
        with FileSource.from_path("tests/embedding/syntax.pyhp", compiler) as source:
            loader = SourceFileLoader("__main__", "tests/embedding/syntax.pyhp")
            spec = importlib.machinery.ModuleSpec(
                "__main__",
                loader,
                origin="tests/embedding/syntax.pyhp",
                is_package=False
            )
            spec.has_location = True
            self.assertEqual(
                source.source().replace(os.linesep, "\n"),  # workaround git automatic newlines
                inspect.getsource(importlib.util.module_from_spec(spec))
            )
        with self.assertRaises(ImportError):
            loader.get_code("test")
        with self.assertRaises(ImportError):
            loader.get_source("test")

    def test_timestamps(self) -> None:
        """test FileSource timestamps"""
        # allow parallel execution of file reading tests
        with FileSource.from_path("tests/__init__.py", compiler) as source:
            info = source.info()
            self.assertEqual(
                info,
                (
                    source.mtime(),
                    source.ctime(),
                    source.atime()
                )
            )
            stat = os.stat("tests/__init__.py")
            self.assertEqual(   # might fail if atime gets recorded for __init__.py
                info,
                (
                    stat.st_mtime_ns,
                    stat.st_ctime_ns,
                    stat.st_atime_ns
                )
            )


class TestDirectory(unittest.TestCase):
    """test Directory"""

    container = Directory(
        "tests/embedding",
        compiler
    )

    abs_container = Directory(
        os.path.abspath("tests/embedding"),
        compiler
    )

    def test_config(self) -> None:
        """test Directory.from_config"""
        self.assertEqual(
            self.container,
            Directory.from_config(
                {
                    "path": "tests/embedding"
                },
                compiler
            )
        )
        self.assertEqual(
            Directory.from_config(
                {
                    "path": "~/test"
                },
                compiler
            ).directory_path,
            os.path.expanduser("~/test")
        )
        with self.assertRaises(ValueError):
            Directory.from_config(
                {
                    "path": 9
                },
                compiler
            )
        with self.assertRaises(ValueError):
            Directory.from_config(
                {
                    "path": "tests/embedding"
                },
                self.container
            )

    def test_access(self) -> None:
        """test Directory code retrieval"""
        for name, source in self.container.items():
            with source:
                path = os.path.join("tests/embedding", name)
                with open(path, "r", newline="") as fd:
                    self.assertEqual(
                        source.code(),
                        compiler.compile_file(fd, SourceFileLoader("__main__", path))
                    )
        with self.assertRaises(KeyError):
            self.container["42"].close()

    def test_iter(self) -> None:
        """test iter(Directory)"""
        files = {   # set -> no order
            "syntax.pyhp",
            "syntax.output",
            "indentation.pyhp",
            "indentation.output",
            "shebang.pyhp",
            "shebang.output"
        }
        self.assertEqual(
            files,
            self.container.keys()
        )
        self.assertEqual(
            files,
            self.abs_container.keys()
        )

    def test_eq(self) -> None:
        """test Directory.__eq__"""
        directories = [
            self.container,
            Directory(
                "null",
                compiler
            ),
            Directory(
                self.container.directory_path,
                compiler2
            ),
            self.abs_container
        ]
        self.assertEqual(
            [self.container],
            [directory for directory in directories if directory == self.container]
        )
        self.assertNotEqual(self.container, 42)

    def test_contains(self) -> None:
        """test Directory.__contains__"""
        for name in self.container.keys():
            self.assertIn(name, self.container)
        self.assertNotIn("abc", self.container)
        self.assertNotIn(1, self.container)

    def test_mtime(self) -> None:
        """test Directory.mtime"""
        self.assertEqual(
            self.container.mtime("syntax.pyhp"),
            os.stat("tests/embedding/syntax.pyhp").st_mtime_ns
        )
        with self.assertRaises(KeyError):
            self.container.mtime("42")

    def test_ctime(self) -> None:
        """test Directory.ctime"""
        self.assertEqual(
            self.container.ctime("syntax.pyhp"),
            os.stat("tests/embedding/syntax.pyhp").st_ctime_ns
        )
        with self.assertRaises(KeyError):
            self.container.ctime("42")

    def test_atime(self) -> None:
        """test Directory.atime"""
        self.assertEqual(
            self.container.atime("syntax.pyhp"),
            os.stat("tests/embedding/syntax.pyhp").st_atime_ns
        )
        with self.assertRaises(KeyError):
            self.container.atime("42")

    def test_info(self) -> None:
        """test Directory.info"""
        stat = os.stat("tests/embedding/syntax.pyhp")
        self.assertEqual(
            self.container.info("syntax.pyhp"),
            SourceInfo(
                stat.st_mtime_ns,
                stat.st_ctime_ns,
                stat.st_atime_ns
            )
        )
        with self.assertRaises(KeyError):
            self.container.info("42")


class TestStrictDirectory(unittest.TestCase):
    """test StrictDirectory"""

    container = StrictDirectory(
        "tests/embedding",
        compiler
    )

    abs_container = StrictDirectory(
        os.path.abspath("tests/embedding"),
        compiler
    )

    def test_traversal(self) -> None:
        """test resistance against path traversal"""
        for name in ("../test1", "a/../../test3", "../testsX"):  # would leave the directory
            with self.assertRaises(LeavesDirectoryError):
                self.container.path(name)
            with self.assertRaises(LeavesDirectoryError):
                self.container.path(name)
        with self.assertRaises(ValueError):     # would leave directory on cwd change
            self.container.path(os.path.abspath("test/embedding/syntax.pyhp"))
        # would not leave directory on cwd change
        self.abs_container.path(os.path.abspath("tests/embedding/syntax.pyhp"))
        for name in ("syntax.pyhp", "../embedding/syntax.pyhp", "./syntax.pyhp"):   # inside path
            self.container.path(name)
            self.abs_container.path(name)

    def test_contains(self) -> None:
        """test StrictDirectory.__contains__"""
        self.assertIn("syntax.pyhp", self.container)
        self.assertNotIn(os.path.abspath("tests/embedding/syntax.pyhp"), self.container)
        self.assertNotIn("abc", self.container)
        self.assertNotIn(1, self.container)
