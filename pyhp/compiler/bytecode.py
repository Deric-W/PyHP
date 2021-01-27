#!/usr/bin/python3

"""Module containing a bytecode code implementation"""
# The compiler.bytecode module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
import ast
import marshal
from types import CodeType
from typing import Dict, List, Tuple, Iterator, Any
from importlib.machinery import ModuleSpec
from . import Code, CodeBuilder


__all__ = ("ByteCode", "ByteCodeBuilder")

GENERATOR_NOOP: List[ast.AST] = [  # to force a generator in case there are no text sections
    ast.Return(
        value=None,     # simple 'return' to end generator before yield
        lineno=1,
        col_offset=0
    ),
    ast.Expr(           # to convince python to make a generator
        value=ast.Yield(
            value=ast.Constant(
                value="",
                lineno=1,
                col_offset=0
            ),
            lineno=1,
            col_offset=0
        ),
        lineno=1,
        col_offset=0
    )
]


class ByteCode(Code):
    """Code implementation using a compiled ast"""
    __slots__ = ("code", "spec")

    code: CodeType

    spec: ModuleSpec

    def __init__(self, code: CodeType, spec: ModuleSpec) -> None:
        """construct a instance with a compiled ast and a spec"""
        self.code = code
        self.spec = spec

    def __getstate__(self) -> Tuple[bytes, ModuleSpec]:     # pickle cant process code objects
        """support pickling"""
        return marshal.dumps(self.code), self.spec

    def __setstate__(self, state: Tuple[bytes, ModuleSpec]) -> None:
        """support pickling"""
        self.code = marshal.loads(state[0])
        self.spec = state[1]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ByteCode):
            return self.code == other.code and self.spec == other.spec
        return NotImplemented

    def execute(self, variables: Dict[str, Any]) -> Iterator[str]:
        """execute the code, yielding the text sections between code sections"""
        variables["__spec__"] = self.spec
        variables["__name__"] = self.spec.name
        variables["__loader__"] = self.spec.loader  # lets hope they remove these constants
        variables["__file__"] = self.spec.origin
        variables["__path__"] = self.spec.submodule_search_locations
        variables["__cached__"] = self.spec.cached
        variables["__package__"] = self.spec.parent
        exec(self.code, variables)                  # create generator
        return variables["<module>"]()              # the compiled generator


class ByteCodeBuilder(CodeBuilder):
    """code builder for the bytecode implementation"""
    __slots__ = ("nodes", "has_text", "optimization_level")

    nodes: List[ast.AST]

    has_text: bool

    optimization_level: int

    def __init__(self, optimization_level: int = -1) -> None:
        """construct a instance with the optimization level to compile code sections"""
        self.nodes = []
        self.has_text = False
        self.optimization_level = optimization_level

    def add_code(self, code: str, offset: int) -> None:
        """add a code section with a section number and line offset"""
        try:
            nodes = [
                ast.increment_lineno(node, offset) for node in ast.parse(code, mode="exec").body
            ]
        except SyntaxError as e:    # set correct lineno and reraise
            if e.lineno is not None:
                e.lineno += offset
            raise
        self.nodes.extend(nodes)

    def add_text(self, text: str, offset: int) -> None:   # pylint: disable=W0613
        """add a text section with a section number and line offset"""
        if text:    # ignore empty sections
            self.nodes.append(
                ast.Expr(
                    value=ast.Yield(
                        value=ast.Constant(
                            value=text,
                            lineno=offset + 1,
                            col_offset=0
                        ),
                        lineno=offset + 1,
                        col_offset=0
                    ),
                    lineno=offset + 1,
                    col_offset=0
                )
            )
            self.has_text = True

    def code(self, spec: ModuleSpec) -> ByteCode:
        """build a code object from the received sections"""
        if self.has_text:   # result will be a generator
            nodes = self.nodes
        else:               # result will be a function, add noop yield
            nodes = self.nodes + GENERATOR_NOOP
        code = compile(
            ast.Module(
                body=[
                    ast.FunctionDef(
                        name="<module>",
                        args=ast.arguments(
                            posonlyargs=[],
                            args=[],
                            kwonlyargs=[],
                            kw_defaults=[],
                            defaults=[]
                        ),
                        body=nodes,
                        decorator_list=[],
                        lineno=1,
                        col_offset=0
                    )
                ],
                type_ignores=[]
            ),
            "<unknown>" if spec.origin is None else spec.origin,
            "exec",
            optimize=self.optimization_level,
            dont_inherit=True
        )
        return ByteCode(code, spec)

    def copy(self) -> ByteCodeBuilder:
        """copy the builder with his current state"""
        builder = self.__class__.__new__(self.__class__)
        builder.nodes = self.nodes.copy()
        builder.has_text = self.has_text
        builder.optimization_level = self.optimization_level
        return builder
