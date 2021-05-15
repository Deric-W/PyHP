#!/usr/bin/python3

"""Module containing php interface utils"""
# The phputils module is part of PyHP (https://github.com/Deric-W/PyHP)
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
from abc import ABCMeta, abstractmethod
from enum import Enum
from tempfile import NamedTemporaryFile
from typing import (
    Deque,
    Callable,
    Any,
    Tuple,
    Mapping,
    BinaryIO,
    Sequence,
    Optional,
    List,
    Iterable,
    Union
)
from werkzeug.datastructures import FileStorage

__all__ = (
    "UPLOAD_SUFFIX",
    "valid_path",
    "SimpleCallbackQueue",
    "ArgumentCallbackQueue",
    "UploadError",
    "FailedStream",
    "StreamFactory",
    "UploadStreamFactory",
    "NullStreamFactory",
    "FilesType"
)

UPLOAD_SUFFIX = ".pyhpupload"   # suffix of files created by uploads


def valid_path(name: Optional[str]) -> bool:
    """check if the name of a stream is a valid path"""
    return name is not None and not (name.startswith("<") and name.endswith(">"))


class SimpleCallbackQueue(Deque[Callable[[], None]]):
    """class implementing a queue of callbacks with no arguments"""
    __slots__ = ()

    def execute(self) -> None:
        """execute callbacks from right to left"""
        while True:
            try:
                callback = self.pop()
            except IndexError:              # consumed all callbacks
                break
            callback()


class ArgumentCallbackQueue(Deque[Tuple[Callable[..., None], Sequence[Any], Mapping[str, Any]]]):
    """class implementing a queue of callbacks to be called with specific arguments"""
    __slots__ = ()

    def execute(self) -> None:
        """execute callbacks from right to left"""
        while True:
            try:
                callback, args, kwargs = self.pop()
            except IndexError:              # consumed all callbacks
                break
            callback(*args, **kwargs)


class UploadError(Enum):
    """error code of an upload"""

    SUCCESS = 0

    UNKNOWN = 1

    MAX_FILES = 2

    DISABLED = 3

    PERMISSION_ERROR = 4


class FailedStream(BinaryIO):
    """replacement for failed upload streams"""
    __slots__ = ("reason",)

    reason: UploadError

    closed = False

    mode = "r+b"

    name = "<failed Stream>"

    def __init__(self, reason: UploadError) -> None:
        self.reason = reason

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FailedStream):
            return self.reason == other.reason
        return NotImplemented

    def __enter__(self) -> FailedStream:
        return self

    def __exit__(self, *args: Any) -> bool:
        pass

    def __iter__(self) -> FailedStream:
        return self

    def __next__(self) -> bytes:
        raise StopIteration

    def fileno(self) -> int:
        raise io.UnsupportedOperation

    def isatty(self) -> bool:
        return False

    def readable(self) -> bool:
        return True

    def read(self, size: Optional[int] = None) -> bytes:
        return b""

    def read1(self, size: Optional[int] = None) -> bytes:
        return b""

    def readall(self) -> bytes:
        return b""

    def readinto(self, b: Any) -> int:
        return 0

    def readinto1(self, b: Any) -> int:
        return 0

    def readline(self, size: Optional[int] = None) -> bytes:
        return b""

    def readlines(self, hint: int = -1) -> List[bytes]:
        return []

    def seekable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = 0) -> int:
        return 0

    def tell(self) -> int:
        return 0

    def truncate(self, size: Optional[int] = None) -> int:
        return 0

    def writable(self) -> bool:
        return True

    def write(self, b: Any) -> int:
        return len(b)

    def writelines(self, lines: Iterable[Any]) -> None:
        pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class StreamFactory(metaclass=ABCMeta):
    """abc for stream factories used by werkzeug"""
    __slots__ = ()

    @abstractmethod
    def __call__(
        self,
        total_content_length: Optional[int] = None,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        content_length: Optional[int] = None
    ) -> BinaryIO:
        raise NotImplementedError


class UploadStreamFactory(StreamFactory):
    """class which provides streams for file uploads"""
    __slots__ = ("directory", "max_files")

    directory: str

    max_files: Optional[int]

    def __init__(self, directory: str, max_files: Optional[int] = None) -> None:
        self.directory = directory
        self.max_files = max_files

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UploadStreamFactory):
            return self.directory == other.directory \
                and self.max_files == other.max_files
        return NotImplemented

    def count_files(self) -> int:
        """return the number of currently uploaded files"""
        with os.scandir(self.directory) as iterator:
            return sum(1 for entry in iterator if entry.is_file() and entry.name.endswith(UPLOAD_SUFFIX))

    def __call__(
        self,
        total_content_length: Optional[int] = None,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        content_length: Optional[int] = None
    ) -> BinaryIO:
        if self.max_files is None or self.max_files > self.count_files():
            try:
                return NamedTemporaryFile(  # type: ignore
                    "w+b",
                    suffix=UPLOAD_SUFFIX,   # ignore files not created by pyhp uploads
                    dir=self.directory,
                    delete=False    # allow for moving and reading/writing
                )
            except PermissionError:
                return FailedStream(UploadError.PERMISSION_ERROR)
            except Exception:
                return FailedStream(UploadError.UNKNOWN)
        return FailedStream(UploadError.MAX_FILES)


class NullStreamFactory(StreamFactory):
    """factory which only provides failed streams"""
    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NullStreamFactory):
            return True
        return NotImplemented

    def __call__(
        self,
        total_content_length: Optional[int] = None,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        content_length: Optional[int] = None
    ) -> FailedStream:
        return FailedStream(UploadError.DISABLED)


class FilesType:
    """entry type of PHPWSGIInterface.FILES wrapping a closed FileStorage"""
    __slots__ = ("file_storage",)

    file_storage: FileStorage

    def __init__(self, file_storage: FileStorage) -> None:
        self.file_storage = file_storage
        file_storage.close()     # allow for reading/writing/moving under windows

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FilesType):
            return self.file_storage == other.file_storage
        return NotImplemented

    def __getitem__(self, key: str) -> Union[str, int]:
        """for allowing PHP-style access"""
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError from e

    @property
    def name(self) -> Optional[str]:
        """the name of the uploaded file"""
        return self.file_storage.filename

    @property
    def type(self) -> str:
        """the MIME type of the file"""
        return self.file_storage.mimetype

    @property
    def size(self) -> int:
        """the size of the file in bytes"""
        name = self.tmp_name
        if name != "":
            return os.stat(name).st_size
        return 0

    @property
    def tmp_name(self) -> str:
        """the path of the uploaded file"""
        try:
            name = self.file_storage.stream.name
        except AttributeError:
            return ""
        if valid_path(name):
            return name
        return ""

    @property
    def error(self) -> int:
        """error code of the upload"""
        stream = self.file_storage.stream
        if isinstance(stream, FailedStream):
            return stream.reason.value
        return UploadError.SUCCESS.value

    def close(self) -> None:
        """remove the file"""
        name = self.tmp_name
        if name != "":
            os.unlink(name)
