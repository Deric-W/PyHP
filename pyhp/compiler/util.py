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
from typing import Optional, TextIO, TypeVar, Mapping, Any
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from . import Parser, CodeBuilder, CodeBuilderDecorator, Code
from .generic import GenericCodeBuilder


__all__ = ("Compiler", "StartingIndentationError", "Dedenter")

WHITESPACE_REGEX = re.compile(r"\s*")   # match zero or more times to match no whitespace too

B = TypeVar("B", bound=CodeBuilder)


class Compiler:
    """Facade to the compiler subsystem"""
    __slots__ = ("parser", "base_builder", "__weakref__")

    parser: Parser

    base_builder: CodeBuilder

    def __init__(self, parser: Parser, builder: CodeBuilder) -> None:
        """construct a instance with a parser and a code builder"""
        self.parser = parser
        self.base_builder = builder

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Compiler):
            return self.parser == other.parser and self.base_builder == other.base_builder
        return NotImplemented

    @classmethod
    def from_config(cls, parser: Parser, config: Mapping[str, Any]) -> Compiler:
        """create a compiler instance from config data"""
        try:
            optimization_level = config["optimization_level"]
        except KeyError:
            optimization_level = -1
        else:
            if not isinstance(optimization_level, int):
                raise ValueError("value of key 'optimization_level' expected to be an int")
        builder = GenericCodeBuilder(optimization_level)
        return cls(
            parser,
            Dedenter(builder) if config.get("dedent", True) else builder
        )

    def builder(self) -> CodeBuilder:
        """get a code builder who is not used by other threads"""
        return self.base_builder.copy()

    def compile_raw(self, source: str, spec: ModuleSpec) -> Code:
        """compile a source string with a spec into a code object"""
        builder = self.builder()
        try:
            if source.startswith("#!"):     # shebang, remove first line
                # line offset of 1 to compensate for removed shebang
                self.parser.build(source.partition("\n")[2], builder, 1)
            else:
                self.parser.build(source, builder)
        except SyntaxError as e:    # change filename
            e.filename = spec.origin
            raise e
        return builder.code(spec)

    def compile_str(self, source: str, origin: str = "<string>", loader: Optional[Loader] = None) -> Code:
        """compile a source string into a code object"""
        return self.compile_raw(source, ModuleSpec("__main__", loader, origin=origin, is_package=False))

    def compile_file(self, file: TextIO, loader: Optional[Loader] = None) -> Code:
        """compile a text stream into a code object"""
        builder = self.builder()
        spec = ModuleSpec("__main__", loader, origin=file.name, is_package=False)
        spec.has_location = True
        first_line = file.readline()
        try:
            if first_line.startswith("#!"):     # shebang, remove first line
                # line offset of 1 to compensate for removed shebang
                self.parser.build(file.read(), builder, 1)
            else:
                self.parser.build(first_line + file.read(), builder)
        except SyntaxError as e:    # change filename
            e.filename = spec.origin
            raise e
        return builder.code(spec)


class StartingIndentationError(IndentationError):
    """Exception raised when a line does not start with the starting indentation"""


class Dedenter(CodeBuilderDecorator[B]):
    """decorator which removes a starting indentation from code sections"""
    __slots__ = ()

    def __init__(self, builder: B) -> None:
        """construct a instance with the builder to decorate"""
        self.builder = builder

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Dedenter):
            return self.builder == other.builder
        return NotImplemented

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
        lines = code.splitlines(keepends=True)  # keep original line endings
        iterator = enumerate(lines)
        for line_offset, line in iterator:  # search for the first line of code
            if self.is_code(line):
                indentation = self.get_indentation(line)    # store offset and indentation
                indentation_offset = line_offset
                lines[line_offset] = line[len(indentation):]    # remove the indentation
                break   # found the first line of code
        else:           # no code found, join lines and return
            self.builder.add_code("".join(lines), offset)
            return None
        for line_offset, line in iterator:  # strip the indentation from the remaining code lines
            if self.is_code(line):
                if line.startswith(indentation):    # if line starts with starting indentation
                    lines[line_offset] = line[len(indentation):]  # remove starting indentation
                else:
                    raise StartingIndentationError(            # raise Exception on bad indentation
                        f"line does not start with the indentation of line {offset + indentation_offset + 1}",
                        (
                            "<unkown>",
                            offset + line_offset + 1,
                            len(indentation),
                            line
                        )
                    )
        self.builder.add_code("".join(lines), offset)     # join the lines back together

    def copy(self) -> Dedenter[B]:
        """copy the dedenter with his current state"""
        dedenter = self.__class__.__new__(self.__class__)
        dedenter.builder = self.builder.copy()
        return dedenter
