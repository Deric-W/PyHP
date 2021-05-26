#!/usr/bin/python3

"""Tests for pyhp.backends.memory"""

import unittest
import unittest.mock
import re
from pyhp.backends.memory import MemorySource, HashMap
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


class TestHashMap(unittest.TestCase):
    """test HashMap"""

    container = HashMap(
        (text, MemorySource(compiler.compile_str(text))) for text in ("a", "b", "c", "d")
    )

    def test_config(self) -> None:
        """test HashMap.from_config"""
        self.assertEqual(
            self.container,
            HashMap.from_config(
                dict((text, text) for text in ("a", "b", "c", "d")),
                compiler
            )
        )
        with self.assertRaises(ValueError):
            HashMap.from_config(
                {"a": 9},
                compiler
            )
        self.assertEqual(
            self.container,
            HashMap.from_config(
                {},
                self.container
            )
        )
        dummy = unittest.mock.Mock(wraps=self.container)
        HashMap.from_config({}, dummy)
        dummy.close.assert_called()

    def test_access(self) -> None:
        """test HashMap code retrieval"""
        for name, source in self.container.items():
            self.assertEqual(
                source.code(),
                compiler.compile_str(name)
            )
