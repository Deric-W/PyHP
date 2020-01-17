#!/usr/bin/python3

"""PyHP cache handler (files with modification time)"""

import marshal  # not pickle because only marshal supports code objects
import os.path
from os import makedirs
from time import time

class Handler:
    def __init__(self, cache_path, file_path, config):
        self.cache_prefix = cache_path
        self.cache_path = os.path.join(os.path.expanduser(cache_path), file_path.strip(os.path.sep) + ".cache")  # use full path to allow indentical named files in different directories with cache_path as root
        self.file_path = file_path
        self.ttl = config.getint("ttl")
        self.max_size = config.getint("max_size")

    def get_cachedir_size(self):        # get size of cache directory (with all sub directories) in Mbytes
        size = 0
        for dirpath, dirnames, filenames in os.walk(self.cache_prefix, followlinks=False):
            size += os.path.getsize(dirpath)        # dont forget the size of the directory
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if not os.path.islink(filepath):        # dont count symlinks
                    size += os.path.getsize(filepath)
        return size/(1000**2)       # bytes --> Mbytes

    def is_available(self):     # if cache directory has free space or the cached file is already existing or max_size < 0
        return self.max_size < 0 or os.path.isfile(self.cache_path) or self.get_cachedir_size() < self.max_size

    def is_outdated(self):      # return True if cache is not created or needs refresh or exceeds ttl
        if os.path.isfile(self.cache_path):     # to prevent Exception if cache not existing
            cache_mtime = os.path.getmtime(self.cache_path)
            file_mtime = os.path.getmtime(self.file_path)
            age = time() - cache_mtime
            return cache_mtime < file_mtime or age > self.ttl > -1      # age > ttl > -1 ignores ttl if -1 or lower
        else:
            return True     # file is not existing --> age = infinite

    def load(self): # load sections
        with open(self.cache_path, "rb") as cache:
            code = marshal.load(cache)
        return code

    def save(self, code):   # save sections
        if not os.path.isdir(os.path.dirname(self.cache_path)):     # directories not already created
            makedirs(os.path.dirname(self.cache_path), exist_ok=True)   # ignore already created directories
        with open(self.cache_path, "wb") as cache:
            marshal.dump(code, cache)

    def close(self):
        pass    # nothing to do
