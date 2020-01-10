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
                file_path = sys.argv[0],    # override if not directly executed
                request_order = ("GET", "POST", "COOKIE"),      # order in wich REQUEST gets updated
                keep_blank_values = True,   # if to not remove "" values
                fallback_value = None,      # fallback value of GET, POST, REQUEST and COOKIE if not None
                enable_post_data_reading = False,   # if not to parse POST and consume stdin in the process
                default_mimetype = "text/html"      # Content-Type header if not been set
                ):
        self.__FILE__ = os.path.abspath(file_path)    # absolute path of script
        self.response_code = 200
        self.headers = [["Content-Type", default_mimetype]]
        self.header_sent = False
        self.header_callback = lambda: None
        self.shutdown_functions = []
        self.shutdown_functions_run = False

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

    # set new response code return the old one
    # if no code has been set it will return 200
    def http_response_code(self, response_code=None):
        old_code = self.response_code
        if response_code is not None:
            self.response_code = response_code
        return old_code     # is the current one if no response code has been provided

    # set http header
    # if replace=True replace existing headers of the same type, else simply add
    def header(self, header, replace=True, http_response_code=None):
        header = header.split("\n")[0]  # prevent header injection
        header = header.split(":", maxsplit=1)  # split header into name and value
        header = [part.strip() for part in header]     # remove whitespace
        if len(header) == 1:     # no value provided
            header.append("")   # add empthy value
        if replace:
            repleaced = False   # indicate if headers of the same type were found
            for i in range(0, len(self.headers)):   # need index for changing headers
                if self.headers[i][0].lower() == header[0].lower():     # found same header
                    self.headers[i][1] = header[1]     # repleace
                    repleaced = True
            if not repleaced:   # header not already set
                self.headers.append(header)
        else:
            self.headers.append(header)

    # list set headers            
    def headers_list(self):
        headers = []
        for header in self.headers:
            headers.append(": ".join(header))   # add header like received by the client
        return headers

    # remove header with matching name
    def header_remove(self, name):
        name = name.lower()
        self.headers = [header for header in self.headers if header[0].lower() != name] # remove headers with same name

    # return if header have been sent
    # unlike the PHP function it does not have file and line arguments
    def headers_sent(self):
        return self.header_sent

    # set calback to be executed just before headers are send
    # callback gets no arguments and the return value is ignored
    def header_register_callback(self, callback):
        if not self.header_sent:
            self.header_callback = callback
            return True
        else:
            return False

    # send headers and execute callback
    # DO NOT call this function from a header callback to prevent infinite recursion
    def send_headers(self):
        self.header_sent = True     # prevent recursion if callback prints output or headers set
        self.header_callback()      # execute callback
        print("Status:" , self.response_code, http.HTTPStatus(self.response_code).phrase)
        for header in self.headers:
            print(": ".join(header))
        print()                     # end of headers

    # make wrapper for target function to call send_headers if wrapped function is used, like print
    # use like print = PyHP.make_header_wrapper(print)
    def make_header_wrapper(self, target=print):
        def wrapper(*args, **kwargs):   # wrapper forwards all args and kwargs to target function
            if not self.header_sent:
                self.send_headers()
            target(*args, **kwargs)     # call target with arguments
        return wrapper

    # set Set-Cookie header, but quote special characters in name and value
    # same with expires as setrawcookie
    def setcookie(self, name, value="", expires=0, path="", domain="", secure=False, httponly=False):
        name = urllib.parse.quote_plus(name)
        value = urllib.parse.quote_plus(value)
        return self.setrawcookie(name, value, expires, path, domain, secure, httponly)

    # set Set-Cookie header
    # if expires is a dict the arguments are read from it
    def setrawcookie(self, name, value="", expires=0, path="", domain="", secure=False, httponly=False):
        if self.header_sent:
            return False
        else:
            if type(expires) == dict:   # options array
                path = expires.get("path", "")
                domain = expires.get("domain", "")
                secure = expires.get("secure", False)
                httponly = expires.get("httponly", False)
                samesite = expires.get("samesite", "")
                expires = expires.get("expires", 0)     # has to happen at the end because it overrides expires
            else:
                samesite = ""       # somehow not as keyword argument in PHP
            cookie = "Set-Cookie: %s=%s" % (name, value)
            if expires != 0:
                cookie += "; " + "Expires=%s" % time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + expires))    # add Expires and Max-Age just in case
                cookie += "; " + "Max-Age=%d" % expires 
            if path != "":
                cookie += "; " + "Path=%s" % path
            if domain != "":
                cookie += "; " + "Domain=%s" % domain
            if secure:
                cookie += "; " + "Secure"
            if httponly:
                cookie += "; " + "HttpOnly"
            if samesite != "":
                cookie += "; " + "SameSite=%s" % samesite
            self.header(cookie, False)
            return True

    # register function to be run at shutdown
    # multiple functions are run in the order they have been registerd
    def register_shutdown_function(self, callback, *args, **kwargs):
        self.shutdown_functions.append((callback, args, kwargs))

    # run the shutdown functions in the order they have been registerd
    # DO NOT call run_shutdown_functions from a shutdown_function, it will cause infinite recursion
    def run_shutdown_functions(self):
        self.shutdown_functions_run = True
        for function, args, kwargs in self.shutdown_functions:
            function(*args, **kwargs)

    # destructor used to run shutdown and header functions if needed
    def __del__(self):
        if not self.header_sent:
            self.send_headers()
        if not self.shutdown_functions_run:
            self.run_shutdown_functions()


# parse get values from query string
def parse_get(keep_blank_values=True):
    return urllib.parse.parse_qs(os.getenv("QUERY_STRING", default=""), keep_blank_values=keep_blank_values)

# parse only post data
def parse_post(keep_blank_values=True):
    environ = os.environ.copy()     # dont modify original environ
    environ["QUERY_STRING"] = ""    # prevent th eparsing of GET
    return cgi.parse(environ=environ, keep_blank_values=keep_blank_values)

# parse cookie string
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
        return ("WARNING: This is the dummy cache handler of the libpyhp module, iam providing no useful functions and are just a fallback", )     # return warning

    def close(self):
        pass


# Class containing a fallback session handler (with no function)
class dummy_session_handler:
    pass