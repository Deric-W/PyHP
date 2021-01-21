#!/usr/bin/python3

"""Package containing the compiler subsystem"""
# The compiler package is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from importlib.machinery import ModuleSpec
from typing import Dict, Iterator, Tuple, Any


__all__ = (
    "Code",
    "CompileError",
    "CodeBuilder",
    "CodeBuilderDecorator",
    "Parser",
    "parsers",  # submodules are imported on demand
    "generic",
    "bytecode",
    "util"
)


class Code(metaclass=ABCMeta):
    """abstract base class for code objects"""
    __slots__ = ()

    @abstractmethod
    def execute(self, variables: Dict[str, Any]) -> Iterator[str]:
        """execute the code, yielding the text sections between code sections"""
        raise NotImplementedError


class CompileError(ValueError):
    """Exception raised when compiling a section fails"""
    __slots__ = ()

    def __init__(self, message: str, section: int) -> None:
        self.args = (message, section)

    @property
    def message(self) -> str:
        """message of the exception"""
        return self.args[0]

    @property
    def section(self) -> int:
        """section of the exception"""
        return self.args[1]

    def __str__(self) -> str:
        message, section = self.args
        return f"[Section {section}] {message}"


class CodeBuilder(metaclass=ABCMeta):
    """abstract base class for all code builders"""
    __slots__ = ()

    def add_code(self, code: str, offset: int) -> None:
        """add a code section with a line offset"""

    def add_text(self, text: str, offset: int) -> None:
        """add a text section with a line offset"""

    @abstractmethod
    def code(self, spec: ModuleSpec) -> Code:
        """build a code object from the received sections"""
        raise NotImplementedError

    @abstractmethod
    def copy(self) -> CodeBuilder:
        """copy the builder with his current state"""
        raise NotImplementedError


class CodeBuilderDecorator(CodeBuilder):
    """abstract base class for code builder decorators"""
    __slots__ = ("builder",)

    builder: CodeBuilder

    def add_code(self, code: str, offset: int) -> None:
        """delegate method call to decorated builder"""
        self.builder.add_code(code, offset)

    def add_text(self, text: str, offset: int) -> None:
        """delegate method call to decorated builder"""
        self.builder.add_text(text, offset)

    def code(self, spec: ModuleSpec) -> Code:
        """delegate method call to decorated builder"""
        return self.builder.code(spec)

    def detach(self) -> CodeBuilder:
        """detach the decorator from the builder, leaving it in a undefined state"""
        return self.builder


class Parser(metaclass=ABCMeta):
    """abstract base class for parsers"""
    __slots__ = ()

    @abstractmethod
    def parse(self, source: str, line_offset: int = 0) -> Iterator[Tuple[str, int, bool]]:
        """parse source code, yielding sections with line offset and bool to indicate if they are code"""
        raise NotImplementedError

    def build(self, source: str, builder: CodeBuilder, line_offset: int = 0) -> None:
        """parse source code and submit the results to the builder"""
        for section, offset, is_code in self.parse(source, line_offset):
            if is_code:
                builder.add_code(section, offset)
            else:
                builder.add_text(section, offset)
