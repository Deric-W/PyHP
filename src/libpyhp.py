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

__all__ = ["PyHP", "dummy_cache_handler", "dummy_session_handler", "parse_get", "parse_post", "parse_cookie", "dict2defaultdict"]

# class containing the implementations
class PyHP:
    def __init__(self,    # build GET, POST, COOKIE, SERVER, REQUEST
                request_order = ("GET", "POST", "COOKIE"),      # order in wich REQUEST gets updated
                keep_blank_values = True,   # if to not remove "" values
                fallback_value = None,      # fallback value of GET, POST, REQUEST and COOKIE if not None
                enable_post_data_reading = False,   # if not to parse POST and consume stdin in the process
                default_mimetype = "text/html"      # Content-Type header if not been set
                ):
        self.__FILE__ = os.path.abspath(sys.argv[0])    # absolute path of script

        self.SERVER = {                                                                           # incomplete (AUTH)
            "PyHP_SELF": os.path.relpath(self.__FILE__, os.getenv("DOCUMENT_ROOT", default=os.curdir)),
            "argv": os.getenv("QUERY_STRING", default=sys.argv),
            "argc": len(sys.argv),
            "GATEWAY_INTERFACE": os.getenv("GATEWAY_INTERFACE", default=""),
            "SERVER_ADDR": os.getenv("SERVER_ADDR", default=""),
            "SERVER_NAME": os.getenv("SERVER_NAME", default=""),
            "SERVER_SOFTWARE": os.getenv("SERVER_SOFTWARE", default=""),
            "SERVER_PROTOCOL": os.getenv("SERVER_PROTOCOL", default=""),
            "REQUEST_METHOD": os.getenv("REQUEST_METHOD", default=""),
            "REQUEST_TIME": int(REQUEST_TIME),
            "REQUEST_TIME_FLOAT": REQUEST_TIME,
            "QUERY_STRING": os.getenv("QUERY_STRING", default=""),
            "DOCUMENT_ROOT": os.getenv("DOCUMENT_ROOT", default=""),
            "HTTP_ACCEPT": os.getenv("HTTP_ACCEPT", default=""),
            "HTTP_ACCEPT_CHARSET": os.getenv("HTTP_ACCEPT_CHARSET", default=""),
            "HTTP_ACCEPT_ENCODING": os.getenv("HTTP_ACCEPT_ENCODING", default=""),
            "HTTP_ACCEPT_LANGUAGE": os.getenv("HTTP_ACCEPT_LANGUAGE", default=""),
            "HTTP_CONNECTION": os.getenv("HTTP_CONNECTION", default=""),
            "HTTP_HOST": os.getenv("HTTP_HOST", default=""),
            "HTTP_REFERER": os.getenv("HTTP_REFERER", default=""),
            "HTTP_USER_AGENT": os.getenv("HTTP_USER_AGENT", default=""),
            "HTTPS": os.getenv("HTTPS", default=""),
            "REMOTE_ADDR": os.getenv("REMOTE_ADDR", default=""),
            "REMOTE_HOST": os.getenv("REMOTE_HOST", default=""),
            "REMOTE_PORT": os.getenv("REMOTE_PORT", default=""),
            "REMOTE_USER": os.getenv("REMOTE_USER", default=""),
            "REDIRECT_REMOTE_USER": os.getenv("REDIRECT_REMOTE_USER", default=""),
            "SCRIPT_FILENAME": self.__FILE__,
            "SERVER_ADMIN": os.getenv("SERVER_ADMIN", default=""),
            "SERVER_PORT": os.getenv("SERVER_PORT", default=""),
            "SERVER_SIGNATURE": os.getenv("SERVER_SIGNATURE", default=""),
            "PATH_TRANSLATED": os.getenv("PATH_TRANSLATED", default=""),
            "SCRIPT_NAME": os.getenv("SCRIPT_NAME", default=""),
            "REQUEST_URI": os.getenv("REQUEST_URI", default=""),
            "PyHP_AUTH_DIGEST": "",
            "PyHP_AUTH_USER": "",
            "PyHP_AUTH_PW": "",
            "AUTH_TYPE": os.getenv("AUTH_TYPE", default=""),
            "PATH_INFO": os.getenv("PATH_INFO", default=""),
            "ORIG_PATH_INFO": os.getenv("PATH_INFO", default="")
        }

        # start processing GET, POST and COOKIE
        self.GET = dict2defaultdict(parse_get(keep_blank_values), fallback_value)
        self.COOKIE = dict2defaultdict(parse_cookie(keep_blank_values), fallback_value)
        if enable_post_data_reading:    # dont consume stdin
            self.POST = dict2defaultdict({}, fallback_value)
        else:       # parse POST and consume stdin
            self.POST = dict2defaultdict(parse_post(keep_blank_values), fallback_value)
        
        # build REQUEST
        self.REQUEST = dict2defaultdict({}, fallback_value)   # empthy REQUEST
        for request in request_order:   # update REQUEST in the order given by request_order
            if request == "GET":
                self.REQUEST.update(self.GET)
            elif request == "POST":
                self.REQUEST.update(self.POST)
            elif request == "COOKIE":
                self.REQUEST.update(self.COOKIE)
            else:   # ignore unknown methods
                pass




def parse_get(keep_blank_values=True):
    return urllib.parse.parse_qs(os.getenv("QUERY_STRING", default=""), keep_blank_values=keep_blank_values)

def parse_post(keep_blank_values=True):
    environ = os.environ.copy()     # dont modify original environ
    environ["QUERY_STRING"] = ""    # prevent th eparsing of GET
    return cgi.parse(environ=environ, keep_blank_values=keep_blank_values)

def parse_cookie(keep_blank_values=True):
    cookie_string = os.getenv("HTTP_COOKIE", default="")
    cookie_dict = {}
    for cookie in cookie_string.split("; "):
        cookie = cookie.split("=", maxsplit=1)  # to allow multiple "=" in value
        if len(cookie) == 1:                    # blank cookie
            if keep_blank_values:
                cookie.append("")
            else:
                continue                        # skip cookie
        if cookie[1] == "" and not keep_blank_values:   # skip cookie
            pass
        else:
            cookie[0] = urllib.parse.unquote_plus(cookie[0])    # unquote name and value
            cookie[1] = urllib.parse.unquote_plus(cookie[1])
            if cookie[0] in cookie_dict:
                cookie_dict[cookie[0]].append(cookie[1])    # key already existing
            else:
                cookie_dict[cookie[0]] = [cookie[1]]        # make new key
    return cookie_dict

# convert the dicts of parse_(get, post, cookie) to defaultdict
def dict2defaultdict(_dict, fallback=None):
    if fallback is None:
        output = {}     # no fallback wanted, use normal dict
    else:
        output = defaultdict(lambda: fallback)
    for key, value in _dict.items():
        if len(value) > 1:   # multiple values, stays list
            output[key] = value
        elif len(value) == 1:   # single element, free from list
            output[key] = value[0]
        else:   # empthy list, use fallback if provided
            pass
    return output



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