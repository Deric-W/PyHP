#!/usr/bin/python3

"""Module containing file implementations"""
# The caching.files module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
import os
import os.path
import io
from locale import getpreferredencoding
from types import CodeType
from typing import Optional, Iterator, Mapping, Any, Union
from importlib.abc import FileLoader
from importlib.machinery import ModuleSpec
from . import (
    SourceInfo,
    TimestampedCodeSource,
    DirectCodeSource,
    CodeSourceContainer
)
from ..compiler import Code
from ..compiler.util import Compiler


__all__ = (
    "FileSource",
    "LeavesDirectoryError",
    "Directory",
    "StrictDirectory"
)

ENCODING = getpreferredencoding(False)


class SourceFileLoader(FileLoader):
    """Loader to allow for source Introspection"""
    __slots__ = ()

    def get_code(self, fullname: str) -> Optional[CodeType]:
        """return None because pyhp files have no regular code object"""
        if fullname != self.name:
            raise ImportError(f"loader for '{self.name}' cannot handle '{fullname}'")
        return None

    def get_source(self, fullname: str) -> str:
        if fullname != self.name:
            raise ImportError(f"loader for '{self.name}' cannot handle '{fullname}'")
        with open(self.path, "r") as fd:
            return fd.read()


class FileSource(TimestampedCodeSource, DirectCodeSource):
    """source for accessing files"""
    __slots__ = ("fd", "compiler", "loader")

    fd: io.FileIO

    compiler: Compiler

    loader: Optional[SourceFileLoader]

    def __init__(self, fd: io.FileIO, compiler: Compiler) -> None:
        self.fd = fd
        self.compiler = compiler
        if isinstance(self.fd.name, str):
            self.loader = SourceFileLoader("__main__", self.fd.name)
        else:
            self.loader = None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FileSource):
            return self.fd.name == other.fd.name \
                and self.compiler == other.compiler
        return NotImplemented

    def code(self) -> Code:
        """load and compile the code object from the file"""
        if isinstance(self.fd.name, str):
            spec = ModuleSpec(
                "__main__",
                self.loader,
                origin=self.fd.name,
                is_package=False
            )
            spec.has_location = True
        else:
            spec = ModuleSpec(
                "__main__",
                None,
                origin=f"<fd {self.fd.name}>",
                is_package=False
            )
        return self.compiler.compile_raw(self.source(), spec)

    def source(self) -> str:
        """retrieve the source code"""
        self.fd.seek(0)     # in case this isnt the first read
        return self.fd.readall().decode(ENCODING)

    def size(self) -> int:
        """retrieve the size of the source code in bytes"""
        return os.fstat(self.fd.fileno()).st_size

    def info(self) -> SourceInfo:
        """retrieve all timestamps in ns"""
        stat = os.fstat(self.fd.fileno())
        return SourceInfo(
            stat.st_mtime_ns,
            stat.st_ctime_ns,
            stat.st_atime_ns
        )

    def mtime(self) -> int:
        """retrieve the modification timestamp in ns"""
        return os.fstat(self.fd.fileno()).st_mtime_ns

    def ctime(self) -> int:
        """retireve the creation timestmp in ns"""
        return os.fstat(self.fd.fileno()).st_ctime_ns

    def atime(self) -> int:
        """retrieve the access timestamp in ns"""
        return os.fstat(self.fd.fileno()).st_atime_ns

    def close(self) -> None:
        """close the file"""
        self.fd.close()


class LeavesDirectoryError(ValueError):
    """Exception raised when a path would reference something outside the directory"""


class Directory(CodeSourceContainer[FileSource]):
    """container of FileSources pointing to a directory"""
    __slots__ = ("path", "compiler")

    path: str

    compiler: Compiler

    def __init__(self, path: str, compiler: Compiler) -> None:
        """create an instance with the path of the directory and a compiler"""
        self.path = path
        self.compiler = compiler

    @classmethod
    def from_config(cls, config: Mapping[str, Any], before: Union[Compiler, CodeSourceContainer]) -> Directory:
        """create a instance from configuration data"""
        if isinstance(before, Compiler):
            path = config["path"]
            if isinstance(path, str):
                return cls(os.path.expanduser(path), before)
            raise ValueError("expected value of key 'path' to be a str representing a path")
        raise ValueError(f"{cls.__name__} does not support decorating another CodeSourceContainer")

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Directory):
            return self.path == other.path \
                and self.compiler == other.compiler
        return NotImplemented

    def __getitem__(self, name: str) -> FileSource:
        """get FileSource instance by path (absolute or relative to the directory)"""
        return FileSource(
            io.FileIO(os.path.join(self.path, name), "r"),
            self.compiler
        )

    def __iter__(self) -> Iterator[str]:
        """yield all files as paths relative to the directory"""
        for dirpath, _, filenames in os.walk(self.path, followlinks=True):
            for filename in filenames:
                yield os.path.relpath(os.path.join(dirpath, filename), self.path)

    def __len__(self) -> int:
        files = 0
        for _, _, filenames in os.walk(self.path, followlinks=True):
            files += len(filenames)
        return files


class StrictDirectory(Directory):
    """container of FileSources pinned to a directory"""
    __slots__ = ()

    def __init__(self, path: str, compiler: Compiler) -> None:
        """create an instance with the path of the directory and a compiler"""
        self.path = os.path.normpath(path)  # prevent .. from conflicting with the commonpath check
        self.compiler = compiler

    def __getitem__(self, name: str) -> FileSource:
        """get FileSource instance by path which does not leave the directory"""
        path = os.path.normpath(    # resolve ..
            os.path.join(
                self.path,
                name
            )
        )
        if os.path.commonpath((self.path, path)) != self.path:  # not commonprefix: /test != /testX
            raise LeavesDirectoryError(f"path {name} would leave directory {self.path}")
        return FileSource(
            io.FileIO(path, "r"),
            self.compiler
        )
