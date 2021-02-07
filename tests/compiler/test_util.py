#!/usr/bin/python3

"""Unit tests for the utilities"""

import re
import unittest
import unittest.mock
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

    def test_raw(self) -> None:
        """test Compiler.compile_raw"""
        source = "text1<?pyhp code1 ?>text2<?pyhp code2 ?>"
        spec = ModuleSpec("__main__", None, origin="Test", is_package=False)
        code = self.compiler.compile_raw(source, spec)
        builder = self.compiler.builder()
        self.compiler.parser.build(source, builder)
        code2 = builder.code(spec)
        self.assertEqual(code, code2)

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

    def test_file_shebang(self) -> None:
        """test the handling of shebangs in files"""
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

    def test_string_shebang(self) -> None:
        """test the handling of shebangs in strings"""
        source = "#!test\ntext1<?pyhp code1 ?>text2<?pyhp code2 ?>"
        code = self.compiler.compile_str(source, "Test")
        builder = self.compiler.builder()
        self.compiler.parser.build("text1<?pyhp code1 ?>text2<?pyhp code2 ?>", builder, 1)
        code2 = builder.code(ModuleSpec("__main__", None, origin="Test", is_package=False))
        self.assertEqual(code, code2)


class TestDedenter(unittest.TestCase):
    """Test the dedenting decorator"""
    def test_get_indentation(self) -> None:
        """test the detection of indentation"""
        self.assertEqual(" \t\t ", util.Dedenter.get_indentation(" \t\t "))
        self.assertEqual("", util.Dedenter.get_indentation("test"))
        self.assertEqual("", util.Dedenter.get_indentation("test \t"))
        self.assertEqual("", util.Dedenter.get_indentation(""))
        self.assertEqual(" ", util.Dedenter.get_indentation(" X  \n"))

    def test_dedent(self) -> None:
        """test the dedentation process"""
        builder = unittest.mock.Mock()
        dedenter = util.Dedenter(builder)
        dedenter.add_code("test", 0)    # no indent
        dedenter.add_code(" test", 0)   # simple indent
        dedenter.add_code(" test\n test", 0)
        dedenter.add_code("\t\t#test\ntest\ntest", 0)   # ignore non code lines
        dedenter.add_code("\t\t#test\n test\n test", 0)
        dedenter.add_code("\t\t\ntest\ntest", 0)
        dedenter.add_code("\ntest", 0)
        builder.add_code.assert_has_calls(
            (
                unittest.mock.call("test", 0),
                unittest.mock.call("test", 0),
                unittest.mock.call("test\ntest", 0),
                unittest.mock.call("\t\t#test\ntest\ntest", 0),
                unittest.mock.call("\t\t#test\ntest\ntest", 0),
                unittest.mock.call("\t\t\ntest\ntest", 0),
                unittest.mock.call("\ntest", 0)
            ),
            any_order=False
        )
        with self.assertRaises(util.StartingIndentationError):
            dedenter.add_code("\ttest\ntest", 0)    # test bad indentation

    def test_copy(self) -> None:
        """test Dedenter.copy"""
        builder = unittest.mock.Mock()
        dedenter = util.Dedenter(builder)
        dedenter2 = dedenter.copy()
        self.assertFalse(dedenter2 is dedenter)
        self.assertFalse(dedenter2.builder is builder)
        dedenter.add_text("test", 0)
        builder.add_text.assert_called_with("test", 0)
        dedenter2.builder.add_text.assert_not_called()

    def test_is_code(self) -> None:
        """test Dedenter.is_code"""
        self.assertTrue(util.Dedenter.is_code("test"))
        self.assertTrue(util.Dedenter.is_code("   test"))
        self.assertFalse(util.Dedenter.is_code("#test"))
        self.assertFalse(util.Dedenter.is_code("  #test"))
        self.assertFalse(util.Dedenter.is_code(""))
        self.assertFalse(util.Dedenter.is_code("\t\t  \n"))

    def test_eq(self) -> None:
        """test Dedenter.__eq__"""
        builder = generic.GenericCodeBuilder(-1)
        self.assertEqual(
            util.Dedenter(builder),
            util.Dedenter(builder)
        )
        self.assertNotEqual(
            util.Dedenter(builder),
            util.Dedenter(generic.GenericCodeBuilder(2))
        )
