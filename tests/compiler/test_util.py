#!/usr/bin/python3

"""Unit tests for the utilities"""

import re
import unittest
from importlib.machinery import ModuleSpec
from pyhp.compiler import util, parsers, generic


class TestCompiler(unittest.TestCase):
    """Test the compiler facade"""

    compiler = util.Compiler(
        parsers.RegexParser(re.compile(r"\<\?pyhp\s"), re.compile(r"\s\?\>")),
        generic.GenericCodeBuilder(-1)
    )

    def test_builder(self) -> None:
        """test if the builder is independent from the compiler"""
        self.assertFalse(self.compiler.builder() is self.compiler.base_builder)

    def test_string(self) -> None:
        """test the compilation of strings"""
        source = "text1<?pyhp code1 ?>text2<?pyhp code2 ?>"
        code = self.compiler.compile_str(source, "Test")
        builder = self.compiler.builder()
        self.compiler.parser.build(source, builder)
        code2 = builder.code(ModuleSpec("__main__", None, origin="Test", is_package=False))
        self.assertEqual(code, code2)

    def test_file(self) -> None:
        """test the compilation of files"""
        path = "./tests/embedding/syntax.pyhp"
        with open(path, "r") as file:
            code = self.compiler.compile_file(file)

        builder = self.compiler.builder()
        spec = ModuleSpec("__main__", None, origin=path, is_package=False)
        spec.has_location = True
        with open(path, "r") as file:
            self.compiler.parser.build(file.read(), builder)
        self.assertEqual(
            code,
            builder.code(spec)
        )

    def test_shebang(self) -> None:
        """test the handling of shebangs"""
        path = "./tests/embedding/shebang.pyhp"
        with open(path, "r") as file:
            code = self.compiler.compile_file(file)
        builder = self.compiler.builder()
        spec = ModuleSpec("__main__", None, origin=path, is_package=False)
        spec.has_location = True
        with open(path, "r") as file:
            file.readline()     # discard shebang
            self.compiler.parser.build(file.read(), builder, 1)
        self.assertEqual(
            code,
            builder.code(spec)
        )
