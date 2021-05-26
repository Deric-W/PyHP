#!/usr/bin/python3

"""Package containing file implementations of timestamp-based caches"""
# The backends.caches.timestamped.files module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only


from __future__ import annotations
import os
import base64
import pickle
from typing import TypeVar, Any, Mapping, Iterator
from . import check_mtime
from .. import (
    CacheSource,
    CacheSourceContainer,
    NotCachedException
)
from ... import (
    ConfigHierarchy,
    TimestampedCodeSource,
    TimestampedCodeSourceContainer
)
from ....compiler import Code


S = TypeVar("S", bound=TimestampedCodeSource)


class FileCacheSource(CacheSource[S]):
    """
    source which caches a TimestampedCodeSource on disk
    WARNING: poor performance when updating files with multiple readers on windows
    """
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
            self.update(code)   # if the cache file could not be replaced carry on
            return code
        try:
            if check_mtime(self.code_source.mtime(), os.fstat(fd).st_mtime_ns, self.ttl):
                return pickle.load(os.fdopen(fd, "rb", closefd=False))  # not outdated
        finally:
            os.close(fd)    # close before self.write to prevent errors on windows
        code = self.code_source.code()  # cache is outdated
        self.update(code)   # if the cache file could not be replaced carry on
        return code

    def update(self, code: Code) -> bool:
        """update the cache file, return if it could be replaced"""
        tmp_path = self.path + ".new"   # prevent potential readers from reading parts of the old AND new cache
        try:
            fd = open(tmp_path, "xb")
        except FileExistsError:  # cache is currently being renewed by another process
            return False
        try:
            pickle.dump(code, fd)
        except BaseException:   # something went wrong, clean up tmp_path
            fd.close()  # close before unlink to prevent errors on windows
            os.unlink(tmp_path)
            raise   # dont hide the error
        else:
            fd.close()  # close before os.replace to prevent errors on windows
        try:
            os.replace(tmp_path, self.path)  # atomic, old readers will continue reading the old cache
        except PermissionError as e:
            os.unlink(tmp_path)     # clean up tmp_path
            winerror = getattr(e, "winerror", None)
            # Somehow windows reports the same winerror if the file is in use
            # or we have invalid permissions.
            # Since we already accessed both files we assume we have permissions
            if winerror == 5 or winerror == 32:     # file is currently used by other readers on windows
                return False
            raise   # we have invalid permissions on posix, reraise
        except BaseException:   # something else went wrong, clean up tmp_path
            os.unlink(tmp_path)
            raise   # dont hide the error
        return True

    def cached(self) -> bool:
        """check if the cache file exists and is up to date"""
        try:
            cache_mtime = os.stat(self.path).st_mtime_ns
        except FileNotFoundError:   # no cached
            return False
        return check_mtime(self.code_source.mtime(), cache_mtime, self.ttl)

    def clear(self) -> None:
        """unlink the cache file"""
        try:
            os.unlink(self.path)
        except FileNotFoundError as e:
            raise NotCachedException("cache already clear") from e


def reconstruct_name(path: str) -> str:
    """reconstruct the name from a file cache path"""
    name, _, _ = os.path.basename(path).rpartition(".")
    return base64.b32decode(name.encode("utf8"), casefold=True).decode("utf8")


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
    def from_config(cls, config: Mapping[str, Any], before: ConfigHierarchy) -> FileCache:
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

    def gc(self) -> int:
        """garbage collect all cached sources and return the number removed"""
        removed = 0
        for path in self.paths():
            name = reconstruct_name(path)
            cache_mtime = os.stat(path).st_mtime_ns
            if not check_mtime(self.source_container.mtime(name), cache_mtime, self.ttl):
                try:
                    os.unlink(path)
                except FileNotFoundError:   # file was already removed
                    pass
                removed += 1
        return removed

    def clear(self) -> None:
        """remove all sources from the cache"""
        for path in self.paths():
            try:
                os.unlink(path)
            except FileNotFoundError:   # file was already removed
                pass

    def path(self, name: str) -> str:
        """return directory_name/<base32 encoded name>.pickle"""
        return os.path.join(
            self.directory_name,
            base64.b32encode(name.encode("utf8")).decode("utf8") + ".pickle"
        )   # use base32 because of case-insensitive file systems and forbidden characters

    def paths(self) -> Iterator[str]:
        """return a iterator yielding all paths currently in use (including outdated ones)"""
        with os.scandir(self.directory_name) as directory:
            for entry in directory:
                if entry.name.endswith(".pickle") and entry.is_file():
                    yield entry.path
