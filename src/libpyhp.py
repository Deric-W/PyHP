#!/usr/bin/python3

# Module containing multiple Python implementations of functions from PHP and utilities
# This module is part of PyHP (https://github.com/Deric-W/PyHP)
"""Module containing multiple Python implementations of functions from PHP and utilities"""

import time
REQUEST_TIME = time.time()   # found no better solution
import sys
import os
import cgi
import http
import urllib.parse
from collections import defaultdict

__all__ = ["PyHP", "dummy_cache_handler", "dummy_session_handler"]

# class containing the implementations
class PyHP:
    pass


# Class containing a fallback cache handler (with no function)
class dummy_cache_handler:
    def __init__(self, cache_path, file_path, config):
        pass

    def is_available(self):
        return False    # we are only a fallback

    def is_outdated(self):
        return False

    def save(self, code):
        pass

    def load(self):
        return ("WARNING: This is the dummy cache handler of the libpyhp module, iam providing no useful functions and are just fallback", )     # return warning

    def close(self):
        pass


# Class containing a fallback session handler (with no function)
class dummy_session_handler:
    pass