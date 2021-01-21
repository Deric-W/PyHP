#!/usr/bin/python3

"""Unit tests for the compiler.parsers module"""

import re
import unittest
from pyhp.compiler import parsers


class TestRegexParser(unittest.TestCase):
    """Test the regex parser implementation"""
    parser = parsers.RegexParser(re.compile("{"), re.compile("}"))

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
