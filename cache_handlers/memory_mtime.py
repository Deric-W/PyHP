#!/usr/bin/python3

"""PyHP cache handler (memory with modification time and LRU cache replacement)"""

import sys
import os.path
from time import time
from threading import Lock
from collections import OrderedDict


class OutdatedError(Exception):
    """exception raised when the cached value is outdated"""
    pass


def code_size(code):
    """claculate the size of a code object"""
    return sum(sys.getsizeof(section) for section in code) + sys.getsizeof(code)


class Handler:
    """Cache handler storing the cache in memory and detecting outdated files with their mtime"""
    renew_exceptions = (OutdatedError, KeyError)

    __slots__ = "cache", "lock", "ttl", "max_size"

    def __init__(self, location, max_size, ttl):
        self.cache = OrderedDict()  # location is ignored
        self.lock = Lock()  # OrderedDict not thread safe
        self.max_size = max_size
        self.ttl = ttl

    def _size(self):
        """get dict size in Mbytes"""
        size = 0
        for file_path, value in self.cache.items():
            size += sys.getsizeof(file_path)
            size += code_size(value)
        return size / (1000 ** 2)   # bytes --> Mbytes

    def is_outdated(self, file_path):
        """return if the cached file is outdated"""
        try:
            cache_mtime = self.cache[file_path][0]
        except KeyError:    # cache not created --> age = infinite
            return True
        else:
            age = time() - cache_mtime
            return cache_mtime < os.path.getmtime(file_path) or 0 <= self.ttl < age      # 0 <= self.ttl < age ignores ttl if lower than zero

    def load(self, file_path):
        """return cached file"""
        if self.is_outdated(file_path):
            raise OutdatedError("the cached file is outated")
        with self.lock:
            self.cache.move_to_end(file_path, last=False)
            return self.cache[file_path][1]

    def save(self, file_path, code):
        """save code in cached file"""
        with self.lock:
            if file_path not in self.cache and 0 <= self.max_size < self._size():   # file not already cached and max_size reached
                size_needed = code_size(code)   # space needed
                while size_needed > 0:  # remove cached objects until there is enough space
                    least_file, least_code = self.cache.popitem()
                    size_needed -= sys.getsizeof(least_file)
                    size_needed -= code_size(least_code)
            self.cache[file_path] = (time(), code)  # store timestamp
            self.cache.move_to_end(file_path, last=False)

    def remove(self, file_path, force=False):
        """remove cached data of file"""
        with self.lock:
            del self.cache[file_path]

    def reset(self):
        """remove entire cache"""
        with self.lock:
            self.cache.clear()

    def shutdown(self):
        """shutdown Handler"""
        self.reset()    # free memory
