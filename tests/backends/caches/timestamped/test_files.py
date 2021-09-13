#!/usr/bin/python3

"""Tests for pyhp.backends.caching.timestamped.files"""

import unittest
import re
import io
import os
import os.path
import sys
import time
import tempfile
from pyhp.backends.files import FileSource, Directory
from pyhp.backends.caches.timestamped.files import (
    FileCacheSource,
    FileCache,
    FILE_EXTENSION
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


class BrokenCode:
    """code objects which fails to pickle"""

    def __getstate__(self) -> None:
        raise RuntimeError

    def __setstate__(self, state) -> None:
        raise RuntimeError


@unittest.skipIf(sys.platform.startswith("win"), "requires Posix")
class TestFileCacheSource(unittest.TestCase):
    """test FileCacheSource"""
    def test_eq(self) -> None:
        """test FileSource.__eq__"""
        sources = [
            FileCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "./tmp.cache"
            ),
            FileCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler
                ),
                "./tmp.cache2"
            ),
            FileCacheSource(
                FileSource(
                    io.FileIO("tests/embedding/syntax.pyhp", "r"),
                    compiler2
                ),
                "./tmp.cache"
            )
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

    def test_code(self) -> None:
        """test FileCacheSource.code"""
        with tempfile.TemporaryDirectory(".") as directory:
            path = os.path.join(directory, "tmp.cache")
            with FileCacheSource(FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler), path, int(1e9)) as source:
                code1 = source.code_source.code()
                self.assertFalse(os.path.exists(path))
                self.assertEqual(code1, source.code())
                self.assertTrue(os.path.exists(path))
                self.assertEqual(code1, source.code())   # check if source can be read multiple times
                time.sleep(1.5)
                self.assertEqual(code1, source.code())
                os.unlink(path)
                open(path + ".new", "wb").close()
                try:
                    self.assertEqual(code1, source.code())
                    self.assertFalse(os.path.exists(path))
                finally:
                    os.unlink(path + ".new")

    def test_update(self) -> None:
        """test FileCacheSource.update error handling"""
        with tempfile.TemporaryDirectory(".") as directory:
            path = os.path.join(directory, "tmp.cache")
            with FileCacheSource(FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler), path) as source:
                with self.assertRaises(RuntimeError):
                    source.update(BrokenCode())
                self.assertFalse(os.path.exists(path + ".new"))

                os.mkdir(path)
                try:
                    with self.assertRaises(IsADirectoryError):
                        source.update(source.code_source.code())
                    self.assertFalse(os.path.exists(path + ".new"))
                finally:
                    os.rmdir(path)

    def test_cached(self) -> None:
        """test FileCacheSource.cached"""
        with tempfile.TemporaryDirectory(".") as directory:
            path = os.path.join(directory, "tmp.cache")
            with FileCacheSource(FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler), path, int(1e9)) as source:
                self.assertFalse(source.cached())
                source.fetch()
                self.assertTrue(source.cached())
                time.sleep(1.5)
                self.assertFalse(source.cached())
                source.fetch()
                os.utime(path, ns=(0, 0))
                self.assertFalse(source.cached())

    def test_clear(self) -> None:
        """test FileCacheSource.clear"""
        with tempfile.TemporaryDirectory(".") as directory:
            path = os.path.join(directory, "tmp.cache")
            with FileCacheSource(FileSource(io.FileIO("tests/embedding/syntax.pyhp", "r"), compiler), path, int(3e9)) as source:
                self.assertFalse(source.clear())
                source.fetch()
                self.assertTrue(source.clear())
                self.assertFalse(os.path.exists(path))
                self.assertFalse(source.clear())


@unittest.skipIf(sys.platform.startswith("win"), "requires Posix")
class TestFileCache(unittest.TestCase):
    """test FileCache"""

    def test_from_config(self) -> None:
        """test FileCache.from_config"""
        container = Directory("tests/embedding", compiler)
        with FileCache.from_config(
            {
                "directory_name": "~"
            },
            container
        ) as cache:
            self.assertEqual(cache.directory_name, os.path.expanduser("~"))
            self.assertEqual(cache.ttl, 0)
        with FileCache.from_config(
            {
                "directory_name": "~",
                "ttl": 9
            },
            container
        ) as cache:
            self.assertEqual(cache.ttl, 9e9)
        with self.assertRaises(KeyError):
            FileCache.from_config({}, container)
        with self.assertRaises(ValueError):
            FileCache.from_config({"directory_name": 9}, container)
        with self.assertRaises(ValueError):
            FileCache.from_config({"directory_name": "~", "ttl": "a"}, container)
        with self.assertRaises(ValueError):
            FileCache.from_config({"directory_name": "~"}, compiler)

    def test_access(self) -> None:
        """test FileCache.__getitem__"""
        with FileCache(Directory("tests/embedding", compiler), "tmp") as cache, \
                cache["syntax.pyhp"] as source:
            self.assertTrue(source.path.startswith("tmp"))
            self.assertEqual(source.ttl, 0)
            self.assertEqual(
                os.path.normpath(source.code_source.fd.name),
                os.path.normpath("tests/embedding/syntax.pyhp")
            )

    def test_eq(self) -> None:
        """test FileCache.__eq__"""
        with FileCache(Directory("tests/embedding", compiler), "tmp") as cache1, \
                FileCache(Directory("tests/embedding", compiler2), "tmp") as cache2, \
                FileCache(Directory("tests/embedding", compiler), "tmp2") as cache3:
            self.assertEqual(cache1, cache1)
            self.assertNotEqual(cache1, cache2)
            self.assertNotEqual(cache2, cache3)
            self.assertNotEqual(1, cache1)

    def test_gc_clear(self) -> None:
        """test FileCache.gc and FileCache.clear"""
        with tempfile.TemporaryDirectory() as directory, \
                FileCache(Directory("tests/embedding", compiler), directory) as cache:
            tmp_file = os.path.join(directory, "tmp.pyhp")
            open(tmp_file, "x").close()
            try:
                with cache["syntax.pyhp"] as source:
                    source.fetch()
                with cache["shebang.pyhp"] as source:
                    source.fetch()
                with cache[tmp_file] as source:
                    source.fetch()
                os.utime(cache.path("shebang.pyhp"), (0, 0))
            finally:
                os.unlink(tmp_file)
            try:
                self.assertEqual(cache.gc(), 2)
                self.assertTrue(os.path.exists(cache.path("syntax.pyhp")))
                self.assertFalse(os.path.exists(cache.path("shebang.pyhp")))
                self.assertFalse(os.path.exists(cache.path(tmp_file)))
            finally:
                cache.clear()

    def test_clear(self) -> None:
        """test FileCache.clear"""
        with tempfile.TemporaryDirectory() as directory, \
                FileCache(Directory("tests/embedding", compiler), directory) as cache:
            with cache["syntax.pyhp"] as source:
                source.fetch()
            with cache["shebang.pyhp"] as source:
                source.fetch()
            self.assertTrue(os.path.exists(cache.path("syntax.pyhp")))
            self.assertTrue(os.path.exists(cache.path("shebang.pyhp")))
            cache.clear()
            self.assertFalse(os.path.exists(cache.path("syntax.pyhp")))
            self.assertFalse(os.path.exists(cache.path("shebang.pyhp")))

    def test_path(self) -> None:
        """test FileCache.path"""
        with FileCache(Directory("tests/embedding", compiler), "tmp") as cache:
            self.assertTrue(cache.path("test").startswith("tmp"))
            self.assertNotEqual(cache.path("test"), cache.path("test2"))
            self.assertNotIn("|", cache.path("|"))
            self.assertEqual(cache.reconstruct_name(cache.path("test2")), "test2")

    def test_paths(self) -> None:
        """test FileCache.paths"""
        with tempfile.TemporaryDirectory() as directory, \
                FileCache(Directory("tests/embedding", compiler), directory) as cache:
            tmp_path = os.path.join(directory, "test.txt")
            dir_path = os.path.join(directory, "test" + FILE_EXTENSION)
            with cache["syntax.pyhp"] as source:
                source.fetch()
            with cache["shebang.pyhp"] as source:
                source.fetch()
            try:
                open(tmp_path, "xb").close()
                try:
                    os.mkdir(dir_path)
                    try:
                        paths = list(cache.paths())
                        self.assertEqual(len(paths), 2)
                        self.assertEqual(   # order not important, use sets
                            set(paths),
                            {
                                cache.path("syntax.pyhp"),
                                cache.path("shebang.pyhp")
                            }
                        )
                    finally:
                        os.rmdir(dir_path)
                finally:
                    os.unlink(tmp_path)
            finally:
                cache.clear()

    def test_reconstruct_name(self) -> None:
        """test FileCache.reconstruct_name"""
        names = [
            "test",
            "test/42/9",
            "äöü|<",
            "\n\n\n"
        ]
        with FileCache(Directory("tests/embedding", compiler), "tmp") as cache:
            for name in names:
                path = cache.path(name)
                self.assertEqual(cache.reconstruct_name(path.lower()), name)
                self.assertEqual(cache.reconstruct_name(path.upper()), name)
