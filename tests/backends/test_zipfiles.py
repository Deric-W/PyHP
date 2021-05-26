#!/usr/bin/python3

"""Tests for pyhp.caching.zipfiles"""

import unittest
import os
import re
import tempfile
import zipfile
import inspect
import importlib.util
from importlib.machinery import ModuleSpec
from datetime import datetime
from pyhp.compiler import parsers, util, generic
from pyhp.backends import zipfiles

compiler = util.Compiler(
    parsers.RegexParser(
        re.compile(r"<\?pyhp\s"),
        re.compile(r"\s\?>")
    ),
    util.Dedenter(
        generic.GenericCodeBuilder(-1)
    )
)

compiler2 = util.Compiler(
    parsers.RegexParser(
        re.compile(r"<\?pyhp\s"),
        re.compile(r"\s\?>")
    ),
    generic.GenericCodeBuilder(0)   # different than compiler!
)


class TestZIPSource(unittest.TestCase):
    """test ZIPSource"""
    def test_eq(self) -> None:
        """test ZIPSource.__eq__"""
        with zipfile.ZipFile("tests/embedding.zip", "r") as file:
            sources = [
                zipfiles.ZIPSource(
                    file,
                    file.getinfo("syntax.pyhp"),
                    compiler
                ),
                zipfiles.ZIPSource(
                    file,
                    file.getinfo("syntax.output"),
                    compiler,
                ),
                zipfiles.ZIPSource(
                    file,
                    file.getinfo("syntax.pyhp"),
                    compiler2
                )
            ]
            try:
                for source in sources:
                    self.assertEqual(
                        [source],
                        [s for s in sources if s == source]
                    )
            finally:
                for source in sources:
                    source.close()

    def test_code(self) -> None:
        """test ZIPSource.code"""
        with open("tests/embedding/syntax.pyhp", "r") as fd, \
                zipfile.ZipFile("tests/embedding.zip") as file, \
                zipfiles.ZIPSource(file, file.getinfo("syntax.pyhp"), compiler) as source:
            code1 = source.code()
            spec = ModuleSpec(
                "__main__",
                zipfiles.ZIPLoader("__main__", file, file.getinfo("syntax.pyhp")),
                origin=os.path.join("tests/embedding.zip", "syntax.pyhp"),
                is_package=False
            )
            spec.has_location = True
            code2 = compiler.compile_raw(
                fd.read(),
                spec
            )
            code3 = source.code()   # check if the source can be read multiple times
            self.assertEqual(code1, code2)
            self.assertEqual(code1, code3)

    def test_spec(self) -> None:
        """test code spec"""
        # the raw fd gets not closed somehow, maybe a bug?
        with zipfile.ZipFile("tests/embedding.zip") as file1, \
                zipfile.ZipFile(os.fdopen(os.open("tests/embedding.zip", os.O_RDONLY), "rb"), "r") as file2, \
                zipfiles.ZIPSource(file1, file1.getinfo("syntax.pyhp"), compiler) as source1, \
                zipfiles.ZIPSource(file2, file2.getinfo("syntax.pyhp"), compiler) as source2:
            spec1 = source1.code().spec  # type: ignore
            spec2 = source2.code().spec  # type: ignore
        self.assertEqual(spec1.name, "__main__")
        self.assertEqual(spec1.origin, os.path.join("tests/embedding.zip", "syntax.pyhp"))
        self.assertTrue(spec1.has_location)
        self.assertEqual(spec2.name, "__main__")
        self.assertFalse(spec2.has_location)

    def test_source(self) -> None:
        """test ZIPSource.source"""
        with open("tests/embedding/syntax.pyhp", "r", newline="\n") as fd, \
                zipfile.ZipFile("tests/embedding.zip") as file, \
                zipfiles.ZIPSource(file, file.getinfo("syntax.pyhp"), compiler) as source:
            self.assertEqual(fd.read(), source.source())

    def test_size(self) -> None:
        """test ZIPSource.size"""
        with zipfile.ZipFile("tests/embedding.zip") as file, \
                zipfiles.ZIPSource(file, file.getinfo("syntax.pyhp"), compiler) as source:
            self.assertEqual(source.size(), len(source.source()))

    def test_introspection(self) -> None:
        """test code introspection"""
        with zipfile.ZipFile("tests/embedding.zip") as file, \
                zipfiles.ZIPSource(file, file.getinfo("syntax.pyhp"), compiler) as source:
            spec = source.code().spec   # type: ignore
            self.assertEqual(
                "\n".join(source.source().splitlines()) + "\n",
                inspect.getsource(importlib.util.module_from_spec(spec))
            )
        with self.assertRaises(ImportError):
            spec.loader.get_code("test")
        with self.assertRaises(ImportError):
            spec.loader.get_source("test")

    def test_timestamps(self) -> None:
        """test ZIPSource timestamps"""
        # allow parallel execution of file reading tests
        with zipfile.ZipFile("tests/embedding.zip") as file, \
                zipfiles.ZIPSource(file, file.getinfo("syntax.pyhp"), compiler) as source:
            mtime_ns = source.mtime()
            self.assertEqual(mtime_ns, int(datetime(2021, 2, 18, 20, 40, 28).timestamp() * 1e+9))
            self.assertEqual(source.info(), (mtime_ns, 0, 0))


class TestZIPFileContainer(unittest.TestCase):
    """test ZIPFile"""

    container = zipfiles.ZIPFile(
        zipfile.ZipFile("tests/embedding.zip", "r"),
        compiler
    )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.container.close()

    def test_config(self) -> None:
        """test ZIPFile.from_config"""
        self.assertEqual(
            self.container,
            zipfiles.ZIPFile.from_config(
                {
                    "path": "tests/embedding.zip"
                },
                self.container.compiler
            )
        )
        with self.assertRaises(KeyError):
            zipfiles.ZIPFile.from_config(
                {},
                compiler
            )
        with self.assertRaises(ValueError):
            zipfiles.ZIPFile.from_config(
                {
                    "path": "tests/embedding.zip",
                    "mode": 9
                },
                compiler
            )
        with self.assertRaises(ValueError):
            zipfiles.ZIPFile.from_config(
                {
                    "path": 8,
                },
                compiler
            )
        with self.assertRaises(ValueError):
            zipfiles.ZIPFile.from_config(
                {
                    "path": "tests/embedding.zip",
                    "pwd": 7
                },
                compiler
            )
        with self.assertRaises(ValueError):
            zipfiles.ZIPFile.from_config(
                {
                    "path": "tests/embedding.zip"
                },
                self.container
            )

    def test_access(self) -> None:
        """test ZIPFile code retrieval"""
        for name, source in self.container.items():
            with source:
                path = os.path.join("tests/embedding", name)
                with open(path, "r", newline="") as fd:
                    self.assertEqual(
                        source.code(),
                        compiler.compile_raw(fd.read(), source.spec)
                    )

    def test_contains(self) -> None:
        """test ZIPFile.__contains__"""
        self.assertIn("syntax.pyhp", self.container)
        self.assertNotIn("abc", self.container)
        self.assertNotIn(1, self.container)

    def test_iter(self) -> None:
        """test iter(ZIPFile)"""
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

    def test_eq(self) -> None:
        """test ZIPFile.__eq__"""
        with tempfile.NamedTemporaryFile("wb") as file:
            containers = [
                self.container,
                zipfiles.ZIPFile(
                    self.container.file,
                    compiler2
                ),
                zipfiles.ZIPFile(
                    zipfile.ZipFile(file, "w"),
                    self.container.compiler
                )
            ]
            try:
                self.assertEqual(
                    [self.container],
                    [container for container in containers if container == self.container]
                )
            finally:
                containers[-1].close()
        self.assertNotEqual(self.container, 1)

    def test_mtime(self) -> None:
        """test ZIPFile.mtime"""
        with self.container["syntax.pyhp"] as source:
            self.assertEqual(
                self.container.mtime("syntax.pyhp"),
                source.mtime()
            )

    def test_ctime(self) -> None:
        """test ZIPFile.ctime"""
        self.assertEqual(self.container.ctime("syntax.pyhp"), 0)

    def test_atime(self) -> None:
        """test ZIPFile.atime"""
        self.assertEqual(self.container.atime("syntax.pyhp"), 0)

    def test_info(self) -> None:
        """test ZIPFile.info"""
        with self.container["syntax.pyhp"] as source:
            self.assertEqual(
                self.container.info("syntax.pyhp"),
                source.info()
            )
