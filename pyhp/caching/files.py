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
import time
import base64
import pickle
from locale import getpreferredencoding
from types import CodeType
from typing import Optional, Iterator, Mapping, Any, Union, TypeVar
from importlib.abc import FileLoader
from importlib.machinery import ModuleSpec
from . import (
    SourceInfo,
    TimestampedCodeSource,
    DirectCodeSource,
    CodeSourceContainer,
    TimestampedCodeSourceContainer,
    CacheSource,
    CacheSourceContainer,
    NotCachedException
)
from ..compiler import Code
from ..compiler.util import Compiler


__all__ = (
    "ENCODING",
    "FileSource",
    "LeavesDirectoryError",
    "Directory",
    "StrictDirectory",
    "FileCacheSource",
    "FileCache"
)

S = TypeVar("S", bound=TimestampedCodeSource)

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

    def __init__(self, fd: io.FileIO, compiler: Compiler) -> None:
        self.fd = fd
        self.compiler = compiler
        if isinstance(self.fd.name, str):
            self.spec = ModuleSpec(
                "__main__",
                SourceFileLoader("__main__", self.fd.name),
                origin=self.fd.name,
                is_package=False
            )
            self.spec.has_location = True
        else:
            self.spec = ModuleSpec(
                "__main__",
                None,
                origin=f"<fd {self.fd.name}>",
                is_package=False
            )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FileSource):
            return self.fd.name == other.fd.name \
                and self.compiler == other.compiler
        return NotImplemented

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
            return self.directory_path == other.directory_path \
                and self.compiler == other.compiler
        return NotImplemented

    def __getitem__(self, name: str) -> FileSource:
        """get FileSource instance by path (absolute or relative to the directory)"""
        return FileSource(
            io.FileIO(self.path(name), "r"),
            self.compiler
        )

    def __contains__(self, name: object) -> bool:   # prevent fd leakage
        if isinstance(name, str):
            return os.path.exists(self.path(name))
        raise TypeError(f"name as to be a str, got '{type(name)}'")

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
        return os.stat(self.path(name)).st_mtime_ns

    def ctime(self, name: str) -> int:
        """retrieve the creation timestamp of name"""
        return os.stat(self.path(name)).st_ctime_ns

    def atime(self, name: str) -> int:
        """retrieve the access timestamp of name"""
        return os.stat(self.path(name)).st_atime_ns

    def info(self, name: str) -> SourceInfo:
        """retireve the info about name"""
        stat = os.stat(self.path(name))
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
        raise TypeError(f"name as to be a str, got '{type(name)}'")

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


class FileCacheSource(CacheSource[S]):
    """source which caches a TimestampedCodeSource on disk"""
    __slots__ = ("path", "ttl")

    path: str

    ttl: int

    def __init__(self, code_source: S, path: str, ttl: int = 0) -> None:
        self.code_source = code_source
        self.path = path
        self.ttl = ttl

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FileCacheSource):
            return self.code_source == other.code_source \
                and self.path == other.path
        return NotImplemented

    def fetch(self) -> None:
        """load the represented code object in the cache"""
        if not self.cached():       # we dont need to load the cache
            self.update(self.code_source.code())

    def code(self) -> Code:
        """retrieve the represented code object"""
        try:
            fd = os.open(self.path, os.O_RDONLY)    # in case the cache file gets cleared before we open it
        except FileNotFoundError:                   # not cached
            code = self.code_source.code()
            self.update(code)
            return code
        try:
            if self.check_mtime(os.fstat(fd).st_mtime_ns):  # up to date
                return pickle.load(os.fdopen(fd, "rb", closefd=False))
        finally:
            os.close(fd)    # close before self.write to prevent errors on windows
        code = self.code_source.code()  # outdated
        self.update(code)
        return code

    def update(self, code: Code) -> None:
        """update the cache file"""
        tmp_path = self.path + ".new"   # prevent potential readers from reading parts of the old AND new cache
        try:
            with open(tmp_path, "xb") as fd:
                pickle.dump(code, fd)
            os.replace(tmp_path, self.path)  # atomic, old readers will continue reading the old cache
        except FileExistsError:  # cache is currently being renewed by another process
            pass
        except BaseException:   # something else happend, clean up tmp_path
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise   # dont hide the error

    def cached(self) -> bool:
        """check if the cache file exists and is up to date"""
        try:
            cache_mtime = os.stat(self.path).st_mtime_ns
        except FileNotFoundError:   # no cached
            return False
        return self.check_mtime(cache_mtime)

    def check_mtime(self, mtime: int) -> bool:
        """check if the timestamp is valid"""
        if mtime < self.code_source.mtime():  # outdated
            return False
        if self.ttl > 0:    # up to date, check ttl
            return self.ttl > (time.time_ns() - mtime)
        return True         # up to date

    def clear(self) -> None:
        """unlink the cache file"""
        try:
            os.unlink(self.path)
        except FileNotFoundError as e:
            raise NotCachedException("cache already clear") from e


class FileCache(CacheSourceContainer[TimestampedCodeSourceContainer[S], FileCacheSource[S]]):
    """file cache which stores all cache files inside a central directory"""
    __slots__ = ("directory_name", "ttl")

    directory_name: str

    ttl: int

    def __init__(self, source_container: TimestampedCodeSourceContainer[S], directory_name: str, ttl: int = 0) -> None:
        self.source_container = source_container
        self.directory_name = directory_name
        self.ttl = ttl

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FileCache):
            return self.source_container == other.source_container \
                and self.directory_name == other.directory_name
        return NotImplemented

    def __getitem__(self, name: str) -> FileCacheSource[S]:
        """get FileCacheSource with path as returned by .path()"""
        return FileCacheSource(
            self.source_container[name],
            self.path(name),
            self.ttl
        )

    @classmethod
    def from_config(cls, config: Mapping[str, Any], before: Union[Compiler, CodeSourceContainer]) -> CentralFileCache:
        """create a instance from configuration data"""
        if isinstance(before, TimestampedCodeSourceContainer):
            directory_name = config["directory_name"]
            if isinstance(directory_name, str):
                ttl = config.get("ttl", 0)
                if isinstance(ttl, (int, float)):
                    return cls(
                        before,
                        os.path.expanduser(directory_name),
                        int(ttl * 1e9)  # convert from s to ns
                    )
                raise ValueError("expected value of key 'ttl' to be a int or float")
            raise ValueError("expected value of key 'directory_name' to be a str")
        raise ValueError(f"{cls.__name__} has to decorate another TimestampedCodeSourceContainer")

    def path(self, name: str) -> str:
        """return directory_name/<base32 encoded name>.pickle"""
        return os.path.join(
            self.directory_name,
            base64.b32encode(name.encode("utf8")).decode("utf8") + ".pickle"
        )   # use base32 because of case-insensitive file systems and forbidden characters
