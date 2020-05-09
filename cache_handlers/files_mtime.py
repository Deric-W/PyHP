#!/usr/bin/python3

"""PyHP cache handler (files with modification time)"""

import marshal  # not pickle because only marshal supports code objects
import os
from errno import EXDEV
from time import time
from shutil import rmtree


CACHE_EXTENSION = ".marshal{0}".format(marshal.version) # use version in extension to prevent exception with new marshal version


class OutOfSpaceError(Exception):
    """Exception raised when the cache directory has no free space left"""
    pass


class OutdatedError(Exception):
    """exception raised when the cached file is outdated"""
    pass


class Handler:
    """Cache handler storing the cache on disk and detecting outdated files with their mtime"""
    renew_exceptions = (FileNotFoundError, OutdatedError) # cache was removed during load() or is outdated

    def __init__(self, location, max_size, ttl):
        """init with cache directory, max directory size in Megabytes and ttl of cached files"""
        self.cache_path = os.path.expanduser(location)    # allow ~ in cache_path
        self.ttl = ttl
        self.max_size = max_size

    # assumes the absence of a directory with the name of the file + the extension ".marshal{marshal.version}" in the same directory as the cached file
    def _cached_path(self, file_path):
        """return path of cached file"""
        return os.path.join(self.cache_path, file_path.strip(os.path.sep) + CACHE_EXTENSION)

    def _cachedir_size(self):
        """get size of the cache directory and its contents in megabytes"""
        size = 0
        for dirpath, _, filenames in os.walk(self.cache_path, followlinks=False):
            size += os.path.getsize(dirpath)        # dont forget the size of the directory
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if not os.path.islink(filepath):        # dont count symlinks
                    try:
                        size += os.path.getsize(filepath)
                    except FileNotFoundError:   # ignore if file was removed
                        pass
        return size / (1000 ** 2)       # bytes --> Mbytes

    def is_outdated(self, file_path):
        """return if cache is not created or is outdated (mtime or ttl)"""
        file_mtime = os.path.getmtime(file_path)
        try:     # to prevent Exception if cache not existing
            cache_mtime = os.path.getmtime(self._cached_path(file_path))
        except FileNotFoundError:
            return True     # file is not existing --> age = infinite
        else:
            age = time() - cache_mtime
            return cache_mtime < file_mtime or age > self.ttl >= 0      # age > ttl >= 0 ignores ttl if lower than zero

    def load(self, file_path):
        """return content of cached file"""
        if self.is_outdated(file_path):
            raise OutdatedError("the cached file is outdated")
        else:
            with open(self._cached_path(file_path), "rb") as cache:
                return marshal.load(cache)

    def save(self, file_path, code):
        """write code to cached file"""
        cached_path = self._cached_path(file_path)
        if self.max_size < 0 or os.path.isfile(cached_path) or self._cachedir_size() < self.max_size:   # file is already cached or the cache has not reached max_size yet
            directory = os.path.dirname(cached_path)
            if not os.path.isdir(directory):     # make sure that the directory exists
                os.makedirs(directory, exist_ok=True)   # ignore already created directories
            tmp_path = cached_path + ".new"     # to prevent potential readers from reading parts of the old AND new cache
            try:
                with open(tmp_path, "xb") as fd:    # if the process does not remove tmp_path or gets killed the saving of this cache entry will always be skipped
                    marshal.dump(code, fd)
                os.replace(tmp_path, cached_path)   # atomic, old readers will continue reading the old cache
            except FileExistsError:   # cache is currently being renewed by another process
                pass
            except OSError as err:
                if err.errno == EXDEV:   # replace failed, clean up tmp_path
                     ensure_unlinked(tmp_path)
                raise   # let the user know that replace failed
        else:
            raise OutOfSpaceError("the cache directory has no free space left")

    def remove(self, file_path, force=False):
        """remove cached file if it is outdated or force = True"""
        if force or self.is_outdated(file_path):
            ensure_unlinked(self._cached_path(file_path))  # prevent Exception if file is not yet created or was removed by another process

    def reset(self):
        """remove entire cache, do not call while the cache is in use!"""
        rmtree(self.cache_path)

    def shutdown(self):
        """shutdown Handler"""
        pass    # nothing to do


def ensure_unlinked(file_path):
    """os.unlink but ignores FileNotFound exception"""
    try:
        os.unlink(file_path)
    except FileNotFoundError:
        pass
