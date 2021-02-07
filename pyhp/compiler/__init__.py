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
from typing import Dict, MutableMapping, Iterator, Tuple, Any, TypeVar, Generic


__all__ = (
    "Code",
    "CodeBuilder",
    "CodeBuilderDecorator",
    "Parser",
    "parsers",      # pylint: disable=E0603
    "generic",      # pylint: disable=E0603
    "bytecode",     # pylint: disable=E0603
    "util"          # pylint: disable=E0603
)

B = TypeVar("B", bound="CodeBuilder")


class Code(metaclass=ABCMeta):
    """abstract base class for code objects"""
    __slots__ = ()

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    @abstractmethod
    def execute(self, variables: Dict[str, Any]) -> Iterator[str]:
        """execute the code, yielding the text sections between code sections"""
        raise NotImplementedError


class CodeBuilder(metaclass=ABCMeta):
    """abstract base class for all code builders"""
    __slots__ = ()

    def __deepcopy__(self, memo: MutableMapping[int, Any]) -> CodeBuilder:
        builder = self.copy()
        memo[id(self)] = builder
        return builder

    def add_code(self, code: str, offset: int) -> None:
        """add a code section with a line offset"""

    def add_text(self, text: str, offset: int) -> None:
        """add a text section with a line offset"""

    @abstractmethod
    def code(self, spec: ModuleSpec) -> Code:
        """build a code object from the received sections"""
        raise NotImplementedError

    @abstractmethod
    def copy(self: B) -> B:
        """copy the builder with his current state"""
        raise NotImplementedError


class CodeBuilderDecorator(Generic[B], CodeBuilder):
    """abstract base class for code builder decorators"""
    __slots__ = ("builder",)

    builder: B

    def add_code(self, code: str, offset: int) -> None:
        """delegate method call to decorated builder"""
        self.builder.add_code(code, offset)

    def add_text(self, text: str, offset: int) -> None:
        """delegate method call to decorated builder"""
        self.builder.add_text(text, offset)

    def code(self, spec: ModuleSpec) -> Code:
        """delegate method call to decorated builder"""
        return self.builder.code(spec)

    def detach(self) -> B:
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
