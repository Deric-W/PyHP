#!/usr/bin/python3

"""Tests for pyhp.caching.memory"""

import unittest
import re
from pyhp.caching.memory import MemorySource, MemorySourceContainer
from pyhp.compiler.parsers import RegexParser
from pyhp.compiler.generic import GenericCodeBuilder
from pyhp.compiler.util import Compiler


compiler = Compiler(
    RegexParser(
        re.compile(r"<\?pyhp\s"),
        re.compile(r"\s\?>")
    ),
    GenericCodeBuilder(-1)
)


class TestMemorySourceContainer(unittest.TestCase):
    """test MemorySourceContainer"""

    container = MemorySourceContainer(
        (text, MemorySource(compiler.compile_str(text))) for text in ("a", "b", "c", "d")
    )

    def test_config(self) -> None:
        """test MemorySourceContainer.from_config"""
        self.assertEqual(
            self.container,
            MemorySourceContainer.from_config(
                dict((text, text) for text in ("a", "b", "c", "d")),
                compiler
            )
        )
        with self.assertRaises(ValueError):
            MemorySourceContainer.from_config(
                {"a": 9},
                compiler
            )
        self.assertEqual(
            self.container,
            MemorySourceContainer.from_config(
                {},
                self.container
            )
        )

    def test_access(self) -> None:
        """test MemorySourceContainer code retrieval"""
        for name, source in self.container.items():
            self.assertEqual(
                source.code(),
                compiler.compile_str(name)
            )
