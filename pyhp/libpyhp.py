#!/usr/bin/python3

# Module containing multiple Python implementations of functions from PHP and utilities
# This module is part of PyHP (https://github.com/Deric-W/PyHP)
"""Module containing multiple Python implementations of functions from PHP and utilities"""

import time
import sys
import os
import cgi
import urllib.parse
from http import HTTPStatus
from collections import defaultdict


__all__ = ["PyHP"]


class PyHP:
    """class containing the php functions"""
    response_code = 200

    header_sent = False
    
    cache_handler = None

    def __init__(self,    # build GET, POST, COOKIE, SERVER, REQUEST
                 file_path=sys.argv[0],    # override if not directly executed
                 request_order=("GET", "POST", "COOKIE"),      # order in wich REQUEST gets updated
                 request_time=None,        # not time.time() because it is only evaluated at import
                 keep_blank_values=True,   # if to not remove "" values
                 fallback_value=None,      # fallback value of GET, POST, REQUEST and COOKIE if not None
                 enable_post_data_reading=False,   # if not to parse POST and consume stdin in the process
                 default_mimetype="text/html",      # Content-Type header if not been set
        ):
        if request_time is None:    # take time of creation
            request_time = time.time()
        self.__FILE__ = os.path.abspath(file_path)    # absolute path of script
        self.headers = [["Content-Type", default_mimetype]]     # init with default mimetype header
        self.header_callback = lambda: None     # dummy callback
        self.shutdown_functions = []

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
            "REQUEST_TIME": int(request_time),
            "REQUEST_TIME_FLOAT": request_time,
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
        self.GET = dict2defaultdict(parse_get(self.SERVER["QUERY_STRING"], keep_blank_values), fallback_value)
        self.COOKIE = dict2defaultdict(parse_cookie(os.getenv("HTTP_COOKIE", default=""), keep_blank_values), fallback_value)
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
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        if type is None and not self.header_sent:    # send headers if no output and no exceptions occured
            self.send_headers()
        self.run_shutdown_functions()
        return False    # we dont handle exceptions

    def http_response_code(self, response_code=None):
        """set new response code return the old one"""
        old_code = self.response_code
        if response_code is not None:
            self.response_code = response_code
        return old_code     # is the current one if no response code has been provided

    # if replace=True replace existing headers of the same type, else simply add
    # if http_response_code is not None set it as new response code
    def header(self, header, replace=True, http_response_code=None):
        """set http header"""
        header = header.splitlines()[0]  # prevent header injection
        header = [part.strip() for part in header.partition(":")[0:3:2]]  # split in name and value and remove whitespace
        if replace:
            self.header_remove(header[0])   # remove headers with same name before adding header
        self.headers.append(header)    # add header
        if http_response_code is not None:  # set response code if given (higher priority than location header)
            self.response_code = http_response_code
        elif header[0].lower() == "location" and not is_redirect(self.response_code):  # set matching response code if code is not 201 or 3xx
            self.response_code = 302
        else:
            pass

    def headers_list(self):
        """list http headers"""
        return [": ".join(header) for header in self.headers]   # list headers like received by the client

    # if name not given remove all headers (set-cookie and content-type too!)
    def header_remove(self, name=None):
        """remove headers with matching name (case-insensitive) or all if name is None"""
        if name is not None:
            name = name.lower()  # header names are case-insensitive
            self.headers = [header for header in self.headers if header[0].lower() != name]  # remove headers with same name
        else:
            self.headers = []   # remove all headers

    # unlike the PHP function it does not have file and line arguments
    def headers_sent(self):
        """return if header have been sent"""
        return self.header_sent

    # callback gets no arguments and the return value is ignored
    def header_register_callback(self, callback):
        """set callback to be executed just before headers are send"""
        if not self.header_sent:
            self.header_callback = callback
            return True
        else:
            return False

    # DO NOT call this function from a header callback to prevent infinite recursion
    def send_headers(self):
        """send headers and execute callback"""
        self.header_sent = True     # prevent recursion if callback prints output
        self.header_callback()      # execute callback
        print("Status: {code} {phrase}".format(code=self.response_code, phrase=HTTPStatus(self.response_code).phrase))
        for header in self.headers:
            print(": ".join(header))
        print()                     # end of headers

    # use like print = PyHP.make_header_wrapper(print)
    def make_header_wrapper(self, target):
        """make wrapper of target function that calls send_headers() if used for the first time"""
        def wrapper(*args, **kwargs):   # wrapper forwards all args and kwargs to target function
            if not self.header_sent:
                self.send_headers()
            target(*args, **kwargs)     # call target with arguments
        return wrapper

    # same behavior with expires as setrawcookie
    # in contrast to php, the samesite keyword argument exists here
    def setcookie(self, name, value="", expires=0, path=None, domain=None, secure=False, httponly=False, samesite=None):
        """set Set-Cookie header, but quote special characters in name and value"""
        name = urllib.parse.quote(name)
        value = urllib.parse.quote(value)
        return self.setrawcookie(name, value, expires, path, domain, secure, httponly, samesite)

    # if expires is a dict the arguments are read from it
    # in contrast to php, the samesite keyword argument exists here
    def setrawcookie(self, name, value="", expires=0, path=None, domain=None, secure=False, httponly=False, samesite=None):
        """set Set-Cookie header"""
        if self.header_sent:
            return False
        else:
            if type(expires) == dict:   # options dict
                path = expires.get("path", None)
                domain = expires.get("domain", None)
                secure = expires.get("secure", False)
                httponly = expires.get("httponly", False)
                samesite = expires.get("samesite", None)
                expires = expires.get("expires", 0)     # has to happen at the end because it overrides expires
            cookie = "Set-Cookie: %s=%s" % (name, value)    # initial header
            if expires != 0:
                cookie += "; Expires=%s" % time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + expires))    # add Expires and Max-Age just in case
                cookie += "; Max-Age=%d" % expires
            if path is not None:
                cookie += "; Path=%s" % path
            if domain is not None:
                cookie += "; Domain=%s" % domain
            if secure:
                cookie += "; Secure"
            if httponly:
                cookie += "; HttpOnly"
            if samesite is not None:
                cookie += "; SameSite=%s" % samesite
            self.header(cookie, False)
            return True
    
    def cache_set_handler(self, handler, register_shutdown=True):
        """set new cache handler and register shutdown function if register_shutdown = True"""
        self.cache_handler = handler
        if register_shutdown:
            self.register_shutdown_function(lambda: handler.shutdown())

    def cache_compile_file(self, file):
        """cache file"""
        try:
            self.cache_handler.cache(file)
        except:
            return False
        else:
            return True
    
    def cache_invalidate(self, file, force=False):
        """removes file from the cache if it is outdated or force = True"""
        if self.cache_handler is None or not self.cache_handler.caching_enabled():
            return False
        else:
            self.cache_handler.invalidate(file, force=force)
            return True
    
    def cache_is_script_cached(self, file):
        """check if a file is cached"""
        return not self.cache_handler.is_outdated(file)
    
    def cache_reset(self):
        """remove the entire cache, maybe not supported while the cache is in use"""
        if self.cache_handler is None or not self.cache_handler.caching_enabled():
            return False
        else:
            self.cache_handler.reset()
            return True

    # multiple functions are run in the order they have been registerd
    def register_shutdown_function(self, callback, *args, **kwargs):
        """register function to be run at shutdown"""
        self.shutdown_functions.append((callback, args, kwargs))

    # DO NOT call run_shutdown_functions from a shutdown_function, it will cause infinite recursion
    def run_shutdown_functions(self):
        """run the shutdown functions in the order they have been registerd"""
        for function, args, kwargs in self.shutdown_functions:
            function(*args, **kwargs)


# parse get values from query_string
def parse_get(query_string, keep_blank_values=True):
    return urllib.parse.parse_qs(query_string, keep_blank_values=keep_blank_values)

# parse post data
def parse_post(keep_blank_values=True):
    environ = os.environ.copy()     # dont modify original environ
    environ["QUERY_STRING"] = ""    # prevent the parsing of GET
    return cgi.parse(environ=environ, keep_blank_values=keep_blank_values)

# parse cookie string
def parse_cookie(cookie_string, keep_blank_values=True):
    cookie_dict = {}
    for cookie in cookie_string.split(";"):
        cookie = cookie.partition("=")[0:3:2]  # split in name and value
        if not keep_blank_values and (is_blank(cookie[0]) or is_blank(cookie[1])):
            continue
        cookie = [urllib.parse.unquote(part.strip()) for part in cookie]    # unquote name and value and remove whitespace
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

# check if the response code is redirecting (201 or 3xx)
def is_redirect(code):
    return code == 201 or code // 100 == 3

# check if string is empthy or just whitespace
def is_blank(string):
    return string == "" or string.isspace()
