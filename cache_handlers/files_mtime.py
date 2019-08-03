#!/usr/bin/python3

"""PyHP cache handler (files with modification time)"""

import marshal
import os.path
from os import makedirs

class handler:
    def __init__(self, cache_path, file_path):
        self.cache_path = os.path.join(cache_path, file_path.strip(os.path.sep) + ".cache")         # use full path to allow indentical named files in different directories with cache_path as root
        self.file_path = file_path

    def is_outdated(self):                                                                          # return True if cache is not created or needs refresh
        if not os.path.isfile(self.cache_path) or os.path.getmtime(self.cache_path) < os.path.getmtime(self.file_path):
            return True
        else:
            return False

    def load(self):
        with open(self.cache_path, "rb") as cache:
            cache_content = marshal.load(cache)
        if len(cache_content) != 2:
            raise ValueError("corrupted cache at " + self.cache_path)
        else:
            return cache_content[0], cache_content[1]                                               # file_content, code_at_begin

    def save(self, file_content, code_at_begin):
        if not os.path.isdir(os.path.dirname(self.cache_path)):                                     # directories not already created
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "wb") as cache:
            marshal.dump([file_content, code_at_begin], cache)

    def close(self):
        pass
