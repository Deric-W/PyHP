#!/usr/bin/python3

"""PyHP cache handler (files with modification time)"""

import marshal  # not pickle because only marshal supports code objects
import os.path
from os import makedirs
from time import time


class Handler:
    def __init__(self, cache_path, max_size, ttl):
        self.cache_path = os.path.expanduser(cache_path)    # allow ~ in cache_path
        self.ttl = ttl
        self.max_size = max_size

    def get_cachedir_size(self):        # get size of cache directory (with all sub directories) in Mbytes
        size = 0
        for dirpath, dirnames, filenames in os.walk(self.cache_path, followlinks=False):
            size += os.path.getsize(dirpath)        # dont forget the size of the directory
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if not os.path.islink(filepath):        # dont count symlinks
                    size += os.path.getsize(filepath)
        return size / (1000 ** 2)       # bytes --> Mbytes

    def is_available(self, file_path):     # if cache directory has free space or the cached file is already existing or max_size < 0
        return self.max_size < 0 or os.path.isfile(mkcached_path(self.cache_path, file_path)) or self.get_cachedir_size() < self.max_size

    def is_outdated(self, file_path):      # return True if cache is not created or needs refresh or exceeds ttl
        cached_path = mkcached_path(self.cache_path, file_path)
        if os.path.isfile(cached_path):     # to prevent Exception if cache not existing
            cache_mtime = os.path.getmtime(cached_path)
            file_mtime = os.path.getmtime(file_path)
            age = time() - cache_mtime
            return cache_mtime < file_mtime or age > self.ttl > -1      # age > ttl > -1 ignores ttl if -1 or lower
        else:
            return True     # file is not existing --> age = infinite

    def load(self, file_path):  # load sections
        with open(mkcached_path(self.cache_path, file_path), "rb") as cache:
            code = marshal.load(cache)
        return code

    def save(self, file_path, code):   # save sections
        cached_path = mkcached_path(self.cache_path, file_path)
        directory = os.path.dirname(cached_path)
        if not os.path.isdir(directory):     # directories not already created
            makedirs(directory, exist_ok=True)   # ignore already created directories
        with open(cached_path, "wb") as cache:
            marshal.dump(code, cache)

    def shutdown(self):
        pass    # nothing to do

# use full path to allow indentical named files in different directories with cache_path as root
def mkcached_path(cache_path, file_path):
    return os.path.join(cache_path, file_path.strip(os.path.sep) + ".cache")