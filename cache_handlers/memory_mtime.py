#!/usr/bin/python3

"""PyHP cache handler (memory with modification time)"""

import sys
import os.path
from time import time

class OutOfSpaceError(Exception):
    """Exception raised when the cache dict has no free space left"""
    pass


class OutdatedError(Exception):
    """exception raised when the cached value is outdated"""
    pass


class Handler:
    """Cache handler storing the cache in memory and detecting outdated files with their mtime"""
    renew_exceptions = (OutdatedError, KeyError)

    def __init__(self, location, max_size, ttl):
        self.cache = {} # location is ignored
        self.max_size = max_size
        self.ttl = ttl

    def _size(self):
        """get dict size in Mbytes"""
        size = 0
        for file_path, value in self.cache.items():
            size += sys.getsizeof(file_path)
            size += sys.getsizeof(value)
            for section in value:
                size += sys.getsizeof(section)
        return size / (1000 ** 2)   # bytes --> Mbytes

    def is_outdated(self, file_path):
        """return if the cached file is outdated"""
        file_mtime = os.path.getmtime(file_path)
        cache_mtime = self.cache[file_path][0]
        age = time() - cache_mtime
        return cache_mtime < file_mtime or age > self.ttl >= 0      # age > ttl >= 0 ignores ttl if lower than zero

    def load(self, file_path):
        """return cached file"""
        if self.is_outdated(file_path):
            raise OutdatedError("the cached file is outated")
        else:
            return self.cache[file_path][1]

    def save(self, file_path, code):
        """save code in cached file"""
        if self.max_size < 0 or file_path in self.cache or self._size() < self.max_size:   # file is already cached or the cache has not reached max_size yet
            self.cache[file_path] = (time(), code)  # store timestamp
        else:
            raise OutOfSpaceError("the cache dict has reached max. size")

    def remove(self, file_path, force=False):
        """remove cached data of file if it is outdated or force = True"""
        if force or self.is_outdated(file_path):
            del self.cache[file_path]

    def reset(self):
        """remove entire cache"""
        self.cache.clear()

    def shutdown(self):
        """shutdown Handler"""
        pass
