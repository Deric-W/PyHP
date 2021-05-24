#!/usr/bin/python3

"""Module containing a generic code implementation"""
# The compiler.generic module is part of PyHP (https://github.com/Deric-W/PyHP)
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
from typing import Dict, Iterator, List, Sequence, Union, Any, Tuple
from importlib.machinery import ModuleSpec
from . import Code, CodeBuilder


__all__ = ("GenericCode", "GenericCodeBuilder")


class GenericCode(Code):
    """Code implementation using a sequence of code objects"""
    __slots__ = ("sections", "spec")

    sections: Sequence[Union[CodeType, str]]

    spec: ModuleSpec

    def __init__(self, sections: Sequence[Union[CodeType, str]], spec: ModuleSpec) -> None:
        """construct a instance with the sections and a spec"""
        self.sections = sections
        self.spec = spec

    def __getstate__(self) -> Tuple[bytes, ModuleSpec]:     # pickle cant process code objects
        """support pickling"""
        return marshal.dumps(self.sections), self.spec

    def __setstate__(self, state: Tuple[bytes, ModuleSpec]) -> None:
        """support pickling"""
        self.sections = marshal.loads(state[0])
        self.spec = state[1]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GenericCode):
            return self.sections == other.sections and self.spec == other.spec
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
        for section in self.sections:
            if isinstance(section, CodeType):
                exec(section, variables)
            else:
                yield section


class GenericCodeBuilder(CodeBuilder):
    """Code builder for the generic code implementation"""
    __slots__ = ("sections", "optimization_level")

    sections: List[Union[ast.AST, str]]

    optimization_level: int

    def __init__(self, optimization_level: int = -1) -> None:
        """construct a instance with the optimization level to compile code sections"""
        self.sections = []
        self.optimization_level = optimization_level

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GenericCodeBuilder):
            return self.sections == other.sections \
                and self.optimization_level == other.optimization_level
        return NotImplemented

    def add_code(self, code: str, offset: int) -> None:
        """add a code section with a line offset"""
        try:
            module = ast.parse(code, "<unknown>", mode="exec")
        except SyntaxError as e:    # set correct lineno and reraise
            if e.lineno is not None:
                e.lineno += offset
            raise
        ast.increment_lineno(module, offset)
        self.sections.append(module)

    def add_text(self, text: str, offset: int) -> None:   # pylint: disable=W0613
        """add a text section with a line offset"""
        if text:    # ignore empty sections
            self.sections.append(text)

    def compile_sections(self, name: str) -> Iterator[Union[CodeType, str]]:
        """compile the code sections"""
        for section in self.sections:
            if isinstance(section, ast.AST):
                yield compile(
                    section,
                    name,
                    "exec",
                    dont_inherit=True,
                    optimize=self.optimization_level
                )
            else:
                yield section

    def code(self, spec: ModuleSpec) -> GenericCode:
        """build a code object from the received sections"""
        if spec.origin is None:
            sections = self.compile_sections("<string>")
        else:
            sections = self.compile_sections(spec.origin)
        return GenericCode(tuple(sections), spec)

    def copy(self) -> GenericCodeBuilder:
        """copy the builder with his current state"""
        builder = self.__class__.__new__(self.__class__)
        builder.sections = self.sections.copy()
        builder.optimization_level = self.optimization_level
        return builder
