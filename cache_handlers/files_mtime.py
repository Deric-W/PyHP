#!/usr/bin/python3

"""PyHP cache handler (files with modification time)"""

import marshal
import os.path
from os import makedirs
from time import time

class handler:
    def __init__(self, cache_path, file_path, config):
        self.__cache_prefix = cache_path
        self.__cache_path = os.path.join(os.path.expanduser(cache_path), file_path.strip(os.path.sep) + ".cache")  # use full path to allow indentical named files in different directories with cache_path as root
        self.__file_path = file_path
        self.__ttl = config.getint("ttl")
        self.__max_size = config.getint("max_size")

    def __get_cachedir_size(self):																	# get size of cache directory (with all sub directories) in Mbytes
        size = 0
        for dirpath, dirnames, filenames in os.walk(self.__cache_prefix):
            size += os.path.getsize(dirpath)														# dont forget the size of the folder
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if not os.path.islink(filepath):													# dont follow symlinks
                    size += os.path.getsize(filepath)
        return size/(1024**2)                                                                       # bytes --> Mbytes

    def is_available(self):                                                                         # if cache directory has free space or the cached file is already existing or max_size < 0
        if self.__max_size < 0 or os.path.isfile(self.__cache_path) or self.__get_cachedir_size() < self.__max_size:
            return True
        else:
            return False

    def is_outdated(self):                                                                          # return True if cache is not created or needs refresh or exceeds ttl
        if os.path.isfile(self.__cache_path):                                                       # to prevent Exception if cache not existing
            cache_mtime = os.path.getmtime(self.__cache_path)
            file_mtime = os.path.getmtime(self.__file_path)
            age = time() - cache_mtime
            if cache_mtime < file_mtime or age > self.__ttl > -1:                                    # age > ttl > -1 ignores ttl if -1 or lower
                return True
            else:
                return False
        else:
            return True

    def load(self):
        with open(self.__cache_path, "rb") as cache:
            cache_content = marshal.load(cache)
        if len(cache_content) != 2:
            raise ValueError("corrupted cache at " + self.__cache_path)
        else:
            return cache_content[0], cache_content[1]                                               # file_content, code_at_begin

    def save(self, file_content, code_at_begin):
        if not os.path.isdir(os.path.dirname(self.__cache_path)):                                   # directories not already created
            makedirs(os.path.dirname(self.__cache_path), exist_ok=True)
        with open(self.__cache_path, "wb") as cache:
            marshal.dump([file_content, code_at_begin], cache)

    def close(self):
        pass
