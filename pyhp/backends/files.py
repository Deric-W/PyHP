#!/usr/bin/python3

"""Module containing file backends"""
# The backends.files module is part of PyHP (https://github.com/Deric-W/PyHP)
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
from typing import Optional, Iterator, Mapping, Any
from importlib.abc import FileLoader
from importlib.machinery import ModuleSpec
from . import (
    ConfigHierarchy,
    SourceInfo,
    TimestampedCodeSource,
    DirectCodeSource,
    TimestampedCodeSourceContainer
)
from ..compiler import Code
from ..compiler.util import Compiler


__all__ = (
    "ENCODING",
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
    __slots__ = ("fd", "compiler", "spec")

    fd: io.FileIO

    compiler: Compiler

    spec: ModuleSpec

    def __init__(self, fd: io.FileIO, spec: ModuleSpec, compiler: Compiler) -> None:
        self.fd = fd
        self.spec = spec
        self.compiler = compiler

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FileSource):
            return self.fd.name == other.fd.name \
                and self.compiler == other.compiler
        return NotImplemented

    @classmethod
    def with_inferred_spec(cls, fd: io.FileIO, compiler: Compiler) -> FileSource:
        """create an instance with a spec inferred from the file"""
        if isinstance(fd.name, str):
            spec = ModuleSpec(
                "__main__",
                SourceFileLoader("__main__", fd.name),
                origin=fd.name,
                is_package=False
            )
            spec.has_location = True
        else:
            spec = ModuleSpec(
                "__main__",
                None,
                origin=f"<fd {fd.name}>",
                is_package=False
            )
        return cls(fd, spec, compiler)

    @classmethod
    def from_path(cls, path: str, compiler: Compiler) -> FileSource:
        """create an instance with a spec inferred from a path"""
        spec = ModuleSpec(
            "__main__",
            SourceFileLoader("__main__", path),
            origin=path,
            is_package=False
        )
        spec.has_location = True
        return cls(io.FileIO(path, "r"), spec, compiler)

    def code(self) -> Code:
        """load and compile the code object from the file"""
        return self.compiler.compile_raw(self.source(), self.spec)

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


class Directory(TimestampedCodeSourceContainer[FileSource]):
    """container of FileSources pointing to a directory"""
    __slots__ = ("directory_path", "compiler")

    directory_path: str

    compiler: Compiler

    def __init__(self, directory_path: str, compiler: Compiler) -> None:
        """create an instance with the path of the directory and a compiler"""
        self.directory_path = directory_path
        self.compiler = compiler

    @classmethod
    def from_config(cls, config: Mapping[str, Any], before: ConfigHierarchy) -> Directory:
        """create a instance from configuration data"""
        if isinstance(before, Compiler):
            path = config["path"]
            if isinstance(path, str):
                return cls(os.path.expanduser(path), before)
            raise ValueError("expected value of key 'path' to be a str representing a path")
        raise ValueError(f"{cls.__name__} does not support decorating another CodeSourceContainer")

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Directory):
            return self.directory_path == other.directory_path \
                and self.compiler == other.compiler
        return NotImplemented

    def __getitem__(self, name: str) -> FileSource:
        """get FileSource instance by path (absolute or relative to the directory)"""
        path = self.path(name)
        try:
            return FileSource.from_path(path, self.compiler)
        except FileNotFoundError as e:
            raise KeyError("file does not exist") from e

    def __contains__(self, name: object) -> bool:   # prevent fd leakage
        if isinstance(name, str):
            return os.path.exists(self.path(name))
        return False

    def __iter__(self) -> Iterator[str]:
        """yield all files as paths relative to the directory"""
        for dirpath, _, filenames in os.walk(self.directory_path, followlinks=True):
            for filename in filenames:
                yield os.path.relpath(os.path.join(dirpath, filename), self.directory_path)

    def __len__(self) -> int:
        files = 0
        for _, _, filenames in os.walk(self.directory_path, followlinks=True):
            files += len(filenames)
        return files

    # more performant than the standart implementations
    def mtime(self, name: str) -> int:
        """retrieve the modification timestamp of name"""
        try:
            return os.stat(self.path(name)).st_mtime_ns
        except FileNotFoundError as e:
            raise KeyError("file does not exist") from e

    def ctime(self, name: str) -> int:
        """retrieve the creation timestamp of name"""
        try:
            return os.stat(self.path(name)).st_ctime_ns
        except FileNotFoundError as e:
            raise KeyError("file does not exist") from e

    def atime(self, name: str) -> int:
        """retrieve the access timestamp of name"""
        try:
            return os.stat(self.path(name)).st_atime_ns
        except FileNotFoundError as e:
            raise KeyError("file does not exist") from e

    def info(self, name: str) -> SourceInfo:
        """retireve the info about name"""
        try:
            stat = os.stat(self.path(name))
        except FileNotFoundError as e:
            raise KeyError("file does not exist") from e
        return SourceInfo(
            stat.st_mtime_ns,
            stat.st_ctime_ns,
            stat.st_atime_ns
        )

    def path(self, name: str) -> str:
        """calculate the path for name"""
        return os.path.join(self.directory_path, name)


class StrictDirectory(Directory):
    """container of FileSources pinned to a directory"""
    __slots__ = ()

    def __init__(self, directory_path: str, compiler: Compiler) -> None:
        """create an instance with the path of the directory and a compiler"""
        # prevent .. from conflicting with the commonpath check
        self.directory_path = os.path.normpath(directory_path)
        self.compiler = compiler

    def __contains__(self, name: object) -> bool:
        if isinstance(name, str):
            try:
                path = self.path(name)
            except ValueError:  # leaves the directory
                return False
            return os.path.exists(path)
        return False

    def path(self, name: str) -> str:
        """calculate the path for name which does not leave the directory"""
        path = os.path.normpath(    # resolve ..
            os.path.join(
                self.directory_path,
                name
            )
        )
        # not commonprefix: /test != /testX
        if os.path.commonpath((self.directory_path, path)) != self.directory_path:
            raise LeavesDirectoryError(f"path {name} would leave directory {self.directory_path}")
        return path
