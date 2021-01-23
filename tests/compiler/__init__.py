#!/usr/bin/python3

"""Unit tests for the abc"""

from __future__ import annotations
import unittest
import unittest.mock
from copy import deepcopy
from typing import Iterator, Tuple, Sequence
from importlib.machinery import ModuleSpec
from pyhp.compiler import CompileError, CodeBuilder, CodeBuilderDecorator, Parser


class PointlessDecorator(CodeBuilderDecorator):
    def __init__(self, builder: CodeBuilder) -> None:
        self.builder = builder

    def copy(self) -> PointlessDecorator:
        return self.__class__(self.builder.copy())


class PointlessParser(Parser):
    parse_result: Sequence[Tuple[str, int, bool]]

    def __init__(self, parse_result: Sequence[Tuple[str, int, bool]]) -> None:
        self.parse_result = parse_result

    def parse(self, source: str, line_offset: int = 0) -> Iterator[Tuple[str, int, bool]]:
        return iter(self.parse_result)


class TestCompileError(unittest.TestCase):
    """test the CompileError"""
    def test_params(self) -> None:
        """test the paramters"""
        error = CompileError("test", 9)
        self.assertEqual(error.message, "test")
        self.assertEqual(error.section, 9)

    def test_raise(self) -> None:
        """test if raising the exception works"""
        with self.assertRaises(CompileError):
            raise CompileError("test", 9)

    def test_str(self) -> None:
        """test if CompileError.__str__ works"""
        str(CompileError("test", 1))


class TestCodeBuilderDecorator(unittest.TestCase):
    """test the CodeBuilderDecorator abc"""
    def test_delegate(self) -> None:
        """test if the default implementation delegates the calls"""
        builder = unittest.mock.Mock()
        decorator = PointlessDecorator(builder)
        decorator.add_code("code", 1, 0)
        decorator.add_text("text", 1, 0)
        spec = ModuleSpec("test", None, origin="<test>", is_package=False)
        decorator.code(spec)
        builder.add_code.assert_called_with("code", 1, 0)
        builder.add_text.assert_called_with("text", 1, 0)
        builder.code.assert_called_with(spec)

    def test_detach(self) -> None:
        """test the default detach implementation"""
        builder = unittest.mock.Mock()
        decorator = PointlessDecorator(builder)
        self.assertIs(decorator.detach(), builder)

    def test_deepcopy(self) -> None:
        """test the deepcopy implementation"""
        builder = unittest.mock.Mock()
        decorator = PointlessDecorator(builder)
        copy1 = decorator.copy()
        copy2 = deepcopy(decorator)
        self.assertIsInstance(copy1, PointlessDecorator)
        self.assertIsInstance(copy2, PointlessDecorator)
        self.assertIsNot(copy1, decorator)
        self.assertIsNot(copy2, decorator)
        self.assertIsNot(copy1.builder, builder)
        self.assertIsNot(copy2.builder, builder)


class TestParser(unittest.TestCase):
    """test the Parser abc"""
    def test_build(self) -> None:
        """test Parser.build"""
        parser = PointlessParser(
            [
                ("text0", 0, False),
                ("code0", 0, True),
                ("text1", 1, False),
                ("code1", 2, True),
                ("code2", 2, True)
            ]
        )
        builder = unittest.mock.Mock()
        parser.build("", builder)
        self.assertEqual(
            builder.method_calls,
            [
                unittest.mock.call.add_text("text0", 1, 0),
                unittest.mock.call.add_code("code0", 2, 0),
                unittest.mock.call.add_text("text1", 3, 1),
                unittest.mock.call.add_code("code1", 4, 2),
                unittest.mock.call.add_code("code2", 5, 2)
            ]
        )
