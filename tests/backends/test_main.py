#!/usr/bin/python3

"""Unit tests for the pyhp-backends cli command"""

import re
import os
import sys
import time
import pickle
import tempfile
import subprocess
import unittest
import unittest.mock
from io import StringIO, BytesIO
from argparse import Namespace
from pyhp.backends import main, files
from pyhp.backends.caches.timestamped.memory import MemoryCache, UnboundedCacheStrategy
from pyhp.compiler import parsers, util, generic


directory = files.Directory(
    "./tests/embedding",
    util.Compiler(
        parsers.RegexParser(
            re.compile(r"<\?pyhp\s"),
            re.compile(r"\s\?>")
        ),
        generic.GenericCodeBuilder(-1)
    )
)


class TestMain(unittest.TestCase):
    """test the cli subcommands"""

    def test_main(self) -> None:
        """test cli entry point"""
        buffer = StringIO()
        self.assertEqual(
            main.main(["-c", "./tests/backends/pyhp.toml", "list"], buffer),
            0
        )
        self.assertEqual(
            buffer.getvalue(),
            "\n".join(map(lambda path: f"'{path}'", directory.keys())) + "\n"
        )

    def test_module(self) -> None:
        """test python -m pyhp.backends"""
        self.assertEqual(
            subprocess.run(         # nosec -> imutable input
                [sys.executable, "-m", "pyhp.backends", "--config", "./pyhp.toml", "list"],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).returncode,
            0
        )

    def test_config(self) -> None:
        """test locating the config file"""
        environ = os.environ.copy()
        environ["PYHPCONFIG"] = "./pyhp.toml"
        self.assertEqual(
            subprocess.run(         # nosec -> imutable input
                [sys.executable, "-m", "pyhp.backends", "list"],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=environ
            ).returncode,
            0
        )

    def test_fetch(self) -> None:
        """test main_fetch"""
        names = ["syntax.pyhp", "shebang.pyhp"]
        buffer = StringIO()
        with MemoryCache(directory, UnboundedCacheStrategy()) as backend:
            self.assertEqual(
                main.main_fetch(backend, Namespace(names=names), buffer),
                0
            )
            for name in names:
                with backend[name] as source:
                    self.assertTrue(source.cached())
        self.assertEqual(buffer.getvalue(), "")
        self.assertEqual(main.main_fetch(directory, Namespace(names=names), buffer), 3)

    def test_gc(self) -> None:
        """test main_gc"""
        names = ["syntax.pyhp", "shebang.pyhp"]
        buffer = StringIO()
        with MemoryCache(directory, UnboundedCacheStrategy(), ttl=1) as backend:
            with backend[names[0]] as source:
                source.fetch()
            time.sleep(0.5)   # clock is not very accurate on windows
            self.assertEqual(
                main.main_gc(backend, Namespace(names=names), buffer),
                0
            )
            self.assertEqual(
                main.main_gc(backend, Namespace(names=names), buffer),
                0
            )
            with backend[names[1]] as source:
                source.fetch()
            time.sleep(0.5)
            self.assertEqual(
                main.main_gc(backend, Namespace(names=[]), buffer),
                0
            )
        self.assertEqual(
            buffer.getvalue(),
            f"Collected '{names[0]}'\nCollected 1 names\n"
        )
        self.assertEqual(main.main_gc(directory, Namespace(names=names), buffer), 3)

    def test_clear(self) -> None:
        """test main_clear"""
        names = ["syntax.pyhp", "shebang.pyhp"]
        buffer = StringIO()
        with MemoryCache(directory, UnboundedCacheStrategy()) as backend:
            sources = [backend[name] for name in names]
            try:
                sources[0].fetch()
                sources[1].fetch()
                self.assertEqual(
                    main.main_clear(backend, Namespace(names=names[0:1]), buffer),
                    0
                )
                self.assertFalse(sources[0].cached())
                self.assertTrue(sources[1].cached())
                sources[0].fetch()
                self.assertEqual(
                    main.main_clear(backend, Namespace(names=[]), buffer),
                    0
                )
                self.assertFalse(sources[0].cached())
                self.assertFalse(sources[1].cached())
            finally:
                sources[0].close()
                sources[1].close()
        self.assertEqual(buffer.getvalue(), "")
        self.assertEqual(main.main_clear(directory, Namespace(names=names), buffer), 3)

    def test_list(self) -> None:
        """test main_list"""
        buffer = StringIO()
        self.assertEqual(
            main.main_list(directory, Namespace(pattern=None, cached=False), buffer),
            0
        )
        self.assertEqual(
            buffer.getvalue(),
            "\n".join(map(lambda path: f"'{path}'", directory.keys())) + "\n"
        )
        buffer.seek(0)
        buffer.truncate(0)
        self.assertEqual(
            main.main_list(directory, Namespace(pattern=None, cached=True), buffer),
            0
        )
        self.assertEqual(
            buffer.getvalue(),
            ""
        )
        buffer.seek(0)
        buffer.truncate(0)
        self.assertEqual(
            main.main_list(directory, Namespace(pattern="syn.*", cached=False), buffer),
            0
        )
        self.assertEqual(
            buffer.getvalue(),
            "\n".join(
                map(
                    lambda path: f"'{path}'",
                    filter(
                        lambda path: path.startswith("syn"),
                        directory.keys()
                    )
                )
            ) + "\n"
        )
        buffer.seek(0)
        buffer.truncate(0)
        with MemoryCache(directory, UnboundedCacheStrategy()) as backend:
            with backend["syntax.pyhp"] as source:
                source.fetch()
            self.assertEqual(
                main.main_list(backend, Namespace(pattern=None, cached=False), buffer),
                0
            )
            self.assertEqual(
                buffer.getvalue(),
                "\n".join(
                    map(
                        lambda path: f"'{path}'{' [cached]' if path.endswith('syntax.pyhp') else ''}",
                        directory.keys()
                    )
                ) + "\n"
            )
            buffer.seek(0)
            buffer.truncate(0)
            self.assertEqual(
                main.main_list(backend, Namespace(pattern=None, cached=True), buffer),
                0
            )
        self.assertEqual(
            buffer.getvalue(),
            "'syntax.pyhp' [cached]\n"
        )

    def test_show(self) -> None:
        """test main_show"""
        buffer = StringIO()
        self.assertEqual(
            main.main_show(directory, Namespace(name="shebang.pyhp"), buffer),
            0
        )
        mtime, ctime, _ = directory.info("shebang.pyhp")
        self.assertRegex(
            buffer.getvalue(),
            f"Name: 'shebang.pyhp'\nmtime: {mtime}\nctime: {ctime}\natime: .+?\ncached: Not supported\n"
        )
        buffer.seek(0)
        buffer.truncate(0)
        with MemoryCache(directory, UnboundedCacheStrategy()) as backend, backend["shebang.pyhp"] as source:
            self.assertEqual(
                main.main_show(backend, Namespace(name="shebang.pyhp"), buffer),
                0
            )
            self.assertEqual(
                buffer.getvalue(),
                "Name: 'shebang.pyhp'\nmtime: Not supported\nctime: Not supported\natime: Not supported\ncached: False\n"
            )
            buffer.seek(0)
            buffer.truncate(0)
            source.fetch()
            self.assertEqual(
                main.main_show(backend, Namespace(name="shebang.pyhp"), buffer),
                0
            )
        self.assertEqual(
            buffer.getvalue(),
            "Name: 'shebang.pyhp'\nmtime: Not supported\nctime: Not supported\natime: Not supported\ncached: True\n"
        )

    def test_dump(self) -> None:
        """test main_dump"""
        buffer = StringIO()
        output = BytesIO()
        self.assertEqual(
            main.main_dump(directory, Namespace(name="syntax.pyhp", output=output, protocol=pickle.DEFAULT_PROTOCOL), buffer),
            0
        )
        self.assertEqual(buffer.getvalue(), "")
        output.seek(0)
        with directory["syntax.pyhp"] as source:
            self.assertEqual(
                source.code(),
                pickle.load(output)
            )


class TestArgs(unittest.TestCase):
    """test the cli argument parsing"""

    def test_subcommand_required(self) -> None:
        """test if subcommands are required"""
        with self.assertRaises(SystemExit):
            main.argparser.parse_args([])

    def test_list(self) -> None:
        """test list subparser"""
        args = main.argparser.parse_args(["list"])
        self.assertIsNone(args.pattern)
        self.assertFalse(args.cached)
        self.assertIs(args.function, main.main_list)
        args = main.argparser.parse_args(["list", "test", "-c"])
        self.assertEqual(args.pattern, "test")
        self.assertTrue(args.cached)
        self.assertIs(args.function, main.main_list)

    def test_show(self) -> None:
        """test show subparser"""
        with self.assertRaises(SystemExit):
            main.argparser.parse_args(["show"])
        args = main.argparser.parse_args(["show", "test"])
        self.assertEqual(args.name, "test")
        self.assertIs(args.function, main.main_show)

    def test_fetch(self) -> None:
        """test fetch subparser"""
        with self.assertRaises(SystemExit):
            main.argparser.parse_args(["fetch"])
        args = main.argparser.parse_args(["fetch", "test", "42"])
        self.assertEqual(args.names, ["test", "42"])
        self.assertIs(args.function, main.main_fetch)

    def test_clear(self) -> None:
        """test clear subparser"""
        args = main.argparser.parse_args(["clear"])
        self.assertEqual(args.names, [])
        self.assertIs(args.function, main.main_clear)
        args = main.argparser.parse_args(["clear", "test", "42"])
        self.assertEqual(args.names, ["test", "42"])
        self.assertIs(args.function, main.main_clear)

    def test_gc(self) -> None:
        """test gc subparser"""
        args = main.argparser.parse_args(["gc"])
        self.assertEqual(args.names, [])
        self.assertIs(args.function, main.main_gc)
        args = main.argparser.parse_args(["gc", "test", "42"])
        self.assertEqual(args.names, ["test", "42"])
        self.assertIs(args.function, main.main_gc)

    def test_dump(self) -> None:
        """test dump subparser"""
        with self.assertRaises(SystemExit):
            main.argparser.parse_args(["dump"])
        with self.assertRaises(SystemExit):
            main.argparser.parse_args(["dump", "test", "42"])
        args = main.argparser.parse_args(["dump", "test"])
        self.assertEqual(args.name, "test")
        self.assertIs(args.output, sys.stdout.buffer)
        self.assertEqual(args.protocol, pickle.DEFAULT_PROTOCOL)
        with tempfile.TemporaryDirectory() as directory:
            test_path = directory + "/testfile"
            # windows does not like the file being open multiple times
            open(test_path, "x").close()
            args = main.argparser.parse_args(
                ["dump", "test", "-p", "42", "-o", test_path]
            )
            self.assertEqual(args.output.name, test_path)
            self.assertEqual(args.protocol, 42)
            args.output.write(b"test")
            args.output.close()
            with open(test_path, "r") as file:
                self.assertEqual(file.read(), "test")
