#!/usr/bin/python3

"""Unit tests for the compiler.parsers module"""

import re
import unittest
from pyhp.compiler import parsers


class TestRegexParser(unittest.TestCase):
    """Test the regex parser implementation"""
    parser = parsers.RegexParser(re.compile("{"), re.compile("}"))

    def test_from_config(self) -> None:
        """test RegexParser.from_config"""
        self.assertEqual(
            self.parser,
            parsers.RegexParser.from_config({"start": "{", "end": "}"})
        )
        self.assertEqual(
            parsers.RegexParser.from_config({}),
            parsers.RegexParser(re.compile(r"<\?pyhp\s"), re.compile(r"\s\?>"))
        )
        with self.assertRaises(Exception):
            parsers.RegexParser.from_config({"start": 42})

    def test_syntax(self) -> None:
        """test basic syntax"""
        sections = list(self.parser.parse("text1{code1}\n{code2}{\ncode3\n}text3\n"))
        self.assertEqual(
            sections,
            [
                ("text1", 0, False),
                ("code1", 0, True),
                ("\n", 0, False),
                ("code2", 1, True),
                ("", 1, False),
                ("\ncode3\n", 1, True),
                ("text3\n", 3, False)
            ]
        )

    def test_missing_end(self) -> None:
        """test behavior on missing end of code section"""
        sections = list(self.parser.parse("text1{code1"))
        self.assertEqual(
            sections,
            [
                ("text1", 0, False),
                ("code1", 0, True)
            ]
        )

    def test_code_start(self) -> None:
        """test behavior on starting code section"""
        sections = list(self.parser.parse("{code1}text1"))
        self.assertEqual(
            sections,
            [
                ("", 0, False),
                ("code1", 0, True),
                ("text1", 0, False)
            ]
        )

    def test_eq(self) -> None:
        """test RegexParser.__eq__"""
        self.assertEqual(
            self.parser,
            parsers.RegexParser(re.compile("{"), re.compile("}"))
        )
        self.assertNotEqual(
            self.parser,
            parsers.RegexParser(re.compile("a"), re.compile("}"))
        )
        self.assertNotEqual(
            self.parser,
            parsers.RegexParser(re.compile("{"), re.compile("b"))
        )
