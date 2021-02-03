#!/usr/bin/python3

"""Module containing utilities"""
# The compiler.util module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
import re
from typing import Optional, TextIO, TypeVar, Generic
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from . import Parser, CodeBuilder, CodeBuilderDecorator, Code


__all__ = ("Compiler", "StartingIndentationError", "Dedenter")

WHITESPACE_REGEX = re.compile(r"\s*")   # match zero or more times to match no whitespace too

P = TypeVar("P", bound=Parser)
B = TypeVar("B", bound=CodeBuilder)


class Compiler(Generic[P, B]):
    """Facade to the compiler subsystem"""
    __slots__ = ("parser", "base_builder")

    parser: P

    base_builder: B

    def __init__(self, parser: P, builder: B) -> None:
        """construct a instance with a parser and a code builder"""
        self.parser = parser
        self.base_builder = builder

    def builder(self) -> B:
        """get a code builder who is not used by other threads"""
        return self.base_builder.copy()

    def compile_str(self, source: str, origin: str = "<string>", loader: Optional[Loader] = None) -> Code:
        """compile a source string into a code object"""
        builder = self.builder()
        if source.startswith("#!"):     # shebang, remove first line
            self.parser.build(source.partition("\n")[2], builder, 1)
        else:
            self.parser.build(source, builder)
        return builder.code(ModuleSpec("__main__", loader, origin=origin, is_package=False))

    def compile_file(self, file: TextIO, loader: Optional[Loader] = None) -> Code:
        """compile a text stream into a code object"""
        builder = self.builder()
        first_line = file.readline()
        if first_line.startswith("#!"):     # shebang, remove first line
            self.parser.build(file.read(), builder, 1)  # line offset of 1 to compensate for removed shebang
        else:
            self.parser.build(first_line + file.read(), builder)
        spec = ModuleSpec("__main__", loader, origin=file.name, is_package=False)
        spec.has_location = True
        return builder.code(spec)


class StartingIndentationError(IndentationError):
    """Exception raised when a line does not start with the starting indentation"""
    __slots__ = ()


class Dedenter(CodeBuilderDecorator[B]):
    """decorator which removes a starting indentation from code sections"""
    __slots__ = ()

    def __init__(self, builder: B) -> None:
        """construct a instance with the builder to decorate"""
        self.builder = builder

    @staticmethod
    def get_indentation(line: str) -> str:
        """get the indentation of a line of code"""
        return WHITESPACE_REGEX.match(line).group(0)    # type: ignore

    @staticmethod
    def is_code(line: str) -> bool:
        """check if the line contains code"""
        return not (not line or line.isspace() or line.lstrip().startswith("#"))

    def add_code(self, code: str, offset: int) -> None:
        """delegate method call to builder with dedented code"""
        lines = code.splitlines()
        indentation = None
        for line_num, line in enumerate(lines):
            if self.is_code(line):                  # ignore lines without code
                if indentation is None:             # first line of code, set starting indentation
                    indentation = self.get_indentation(line)
                if line.startswith(indentation):    # if line starts with starting indentation
                    lines[line_num] = line[len(indentation):]  # remove starting indentation
                else:
                    raise StartingIndentationError(            # raise Exception on bad indentation
                        f"line does not start with the indentation of line {offset + 1}",
                        (
                            "<unkown>",
                            line_num + offset + 1,
                            len(indentation),
                            line
                        )
                    )
        self.builder.add_code("\n".join(lines), offset)     # join the lines back together

    def copy(self) -> Dedenter[B]:
        """copy the dedenter with his current state"""
        dedenter = self.__class__.__new__(self.__class__)
        dedenter.builder = self.builder.copy()
        return dedenter
