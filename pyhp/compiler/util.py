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

from typing import Optional, TextIO
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from . import Parser, CodeBuilder, Code


__all__ = ("Compiler",)


class Compiler:
    """Facade to the compiler subsystem"""
    __slots__ = ("parser", "base_builder")

    parser: Parser

    base_builder: CodeBuilder

    def __init__(self, parser: Parser, builder: CodeBuilder) -> None:
        """construct a instance with a parser and a code builder"""
        self.parser = parser
        self.base_builder = builder

    def builder(self) -> CodeBuilder:
        """get a code builder who is not used by other threads"""
        return self.base_builder.copy()

    def compile_str(self, source: str, origin: str = "<string>", loader: Optional[Loader] = None) -> Code:
        """compile a source string into a code object"""
        builder = self.builder()
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
