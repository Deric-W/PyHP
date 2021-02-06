#!/usr/bin/python3

"""Module containing memory implementations"""
# The caching.memory module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
from typing import Dict, Mapping, Any, Union
from . import (
    CodeSource,
    CodeSourceContainer
)
from ..compiler import Code
from ..compiler.util import Compiler


__all__ = (
    "MemorySource",
    "MemorySourceContainer",
)


class MemorySource(CodeSource):
    """in-memory code source"""
    __slots__ = ("code_obj",)

    code_obj: Code

    def __init__(self, code: Code) -> None:
        self.code_obj = code

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MemorySource):
            return self.code_obj == other.code_obj
        return NotImplemented

    def code(self) -> Code:
        """retrieve the stored code object"""
        return self.code_obj


class MemorySourceContainer(Dict[str, MemorySource], CodeSourceContainer[MemorySource]):
    """in-memory code storage"""
    __slots__ = ()

    @classmethod
    def from_config(cls, config: Mapping[str, Any], before: Union[Compiler, CodeSourceContainer]) -> MemorySourceContainer:
        """create a instance from configuration data"""
        if isinstance(before, Compiler):
            container = cls()
            for name, code in config.items():   # config consists of multiple 'name = source code'
                if isinstance(code, str):
                    container[name] = MemorySource(before.compile_str(code))
                else:
                    raise ValueError(
                        f"expected value of key '{name}' to be a string to compile"
                    )
            return container
        raise ValueError(f"{cls.__name__} does not support decorating another CodeSourceContainer")
