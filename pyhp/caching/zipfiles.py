#!/usr/bin/python3

"""Module containing zipfile implementations"""
# The caching.zipfiles module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
import os
import io
import zipfile
from datetime import datetime
from importlib.abc import InspectLoader
from importlib.machinery import ModuleSpec
from locale import getpreferredencoding
from types import CodeType
from typing import IO, Union, Mapping, Any, Iterator, Optional, Tuple
from . import (
    SourceInfo,
    TimestampedCodeSource,
    DirectCodeSource,
    CodeSourceContainer,
    TimestampedCodeSourceContainer
)
from ..compiler import Code
from ..compiler.util import Compiler


__all__ = (
    "ENCODING",
    "ZIPSource",
    "ZIPFile"
)

ENCODING = getpreferredencoding(False)


def datetime_to_ns(date_time: Tuple[int, int, int, int, int, int]) -> int:
    """convert ZipInfo.date_time to a ns timestamp"""
    return int(datetime(*date_time).timestamp() * 1e+9)


class ZIPLoader(InspectLoader):
    """Loader to allow for source Introspection"""
    __slots__ = ("name", "file", "entry")

    name: str

    file: zipfile.ZipFile

    entry: zipfile.ZipInfo

    def __init__(self, name: str, file: zipfile.ZipFile, entry: zipfile.ZipInfo) -> None:
        self.name = name
        self.file = file
        self.entry = entry

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ZIPLoader):
            return self.name == other.name \
                and self.file == other.file \
                and self.entry == other.entry
        return NotImplemented

    def get_code(self, fullname: str) -> Optional[CodeType]:
        """return None because pyhp files have no regular code object"""
        if fullname != self.name:
            raise ImportError(f"loader for '{self.name}' cannot handle '{fullname}'")
        return None

    def get_source(self, fullname: str) -> str:
        if fullname != self.name:
            raise ImportError(f"loader for '{self.name}' cannot handle '{fullname}'")
        with io.TextIOWrapper(self.file.open(self.entry, "r"), ENCODING) as fd:
            return fd.read()


class ZIPSource(TimestampedCodeSource, DirectCodeSource):
    """code source for accessing zip file entries"""
    __slots__ = ("reader", "entry", "compiler", "spec")

    reader: IO[bytes]

    entry: zipfile.ZipInfo

    compiler: Compiler

    spec: ModuleSpec

    def __init__(self, zipfile: zipfile.ZipFile, entry: zipfile.ZipInfo, compiler: Compiler) -> None:
        self.reader = zipfile.open(entry, "r")
        self.entry = entry
        self.compiler = compiler
        if isinstance(zipfile.filename, str):
            origin = os.path.join(zipfile.filename, entry.filename)
            has_location = True
        else:
            origin = f"<zip entry '{entry.filename}'>"
            has_location = False
        self.spec = ModuleSpec(
            "__main__",
            ZIPLoader("__main__", zipfile, entry),
            origin=origin,
            is_package=False
        )
        self.spec.has_location = has_location

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ZIPSource):
            return self.entry == other.entry \
                and self.compiler == other.compiler
        return NotImplemented

    def code(self) -> Code:
        """load and compile the code object from the zipfile"""
        return self.compiler.compile_raw(self.source(), self.spec)

    def source(self) -> str:
        """retrieve the source code"""
        self.reader.seek(0)     # in case this isnt the first read
        return self.reader.read().decode(ENCODING)

    def size(self) -> int:
        """retrieve the size of the source code in bytes"""
        return self.entry.file_size

    def mtime(self) -> int:
        """retrieve the modification timestamp in ns"""
        return datetime_to_ns(self.entry.date_time)

    def ctime(self) -> int:
        """retireve the creation timestmp in ns"""
        return 0    # not available

    def atime(self) -> int:
        """retrieve the access timestamp in ns"""
        return 0    # not available

    def close(self) -> None:
        """close the reader"""
        self.reader.close()


class ZIPFile(TimestampedCodeSourceContainer[ZIPSource]):
    """CodeSourceContainer wrapping zipfile.ZipFile"""
    __slots__ = ("file", "compiler")

    file: zipfile.ZipFile

    compiler: Compiler

    @classmethod
    def from_config(cls, config: Mapping[str, Any], before: Union[Compiler, CodeSourceContainer]) -> ZIPFile:
        """create an instance from configuration data containing path and mode"""
        if isinstance(before, Compiler):
            path = config["path"]
            if isinstance(path, str):
                mode = config.get("mode", "r")  # default
                if isinstance(mode, str):
                    file = zipfile.ZipFile(path, mode)
                    try:
                        pwd = config["pwd"].encode("utf8")
                    except KeyError:
                        pass
                    except Exception as e:
                        file.close()
                        raise ValueError("error while handling value of key 'pwd'") from e
                    else:
                        file.setpassword(pwd)
                    return cls(file, before)
                raise ValueError("expected value of key 'mode' to be a str")
            raise ValueError("expected value of key 'path' to be a str")
        raise ValueError(f"{cls.__name__} can not be used to decorate another CodeSourceContainer")

    def __init__(self, file: zipfile.ZipFile, compiler: Compiler) -> None:
        """create an instance from a zipfile and a compiler object"""
        self.file = file
        self.compiler = compiler

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ZIPFile):
            return self.file.filename == other.file.filename \
                and self.compiler == other.compiler
        return NotImplemented

    def __getitem__(self, name: str) -> ZIPSource:
        return ZIPSource(
            self.file,
            self.file.getinfo(name),
            self.compiler
        )

    def __contains__(self, name: object) -> bool:
        if isinstance(name, str):
            try:
                self.file.getinfo(name)
            except KeyError:
                return False
            return True
        raise TypeError(f"name expected to be str, not '{type(name)}'")

    def __iter__(self) -> Iterator[str]:
        return iter(self.file.namelist())

    def __len__(self) -> int:
        return len(self.file.infolist())

    # more performant than the standart implementation
    def mtime(self, name: str) -> int:
        """retrieve the modification timestamp of name"""
        return datetime_to_ns(self.file.getinfo(name).date_time)

    def ctime(self, name: str) -> int:
        """retrieve the creation timestamp of name"""
        return 0

    def atime(self, name: str) -> int:
        """retrieve the access timestamp of name"""
        return 0

    def info(self, name: str) -> SourceInfo:
        """retireve the info about name"""
        return SourceInfo(
            self.mtime(name),
            0,
            0
        )

    def close(self) -> None:
        """close the wrapped ZipFile"""
        self.file.close()
