#!/usr/bin/python3

"""Module containing the main function(s) of the PyHP Interpreter"""
# This module is part of PyHP (https://github.com/Deric-W/PyHP)

import sys
import os
import argparse
import configparser
import importlib
import errno
from . import __version__
from . import embed
from . import libpyhp


# get cli arguments for main as dict
def get_args():
    parser = argparse.ArgumentParser(prog="pyhp", description="Interpreter for .pyhp Scripts (https://github.com/Deric-W/PyHP)")
    parser.add_argument("-c", "--caching", help="enable caching (requires file)", action="store_true")
    parser.add_argument("-v", "--version", help="display version number", action="version", version="%(prog)s {version}".format(version=__version__))
    parser.add_argument("file", type=str, help="file to be interpreted (omit for reading from stdin)", nargs="?", default="")
    parser.add_argument("--config", type=str, help="path to custom config file", nargs="?", const="/etc/pyhp.conf", default="/etc/pyhp.conf")
    args = parser.parse_args()
    return {"file_path": args.file, "caching": args.caching, "config_file": args.config}

# start the PyHP Interpreter with predefined arguments
def main(file_path, caching=False, config_file="/etc/pyhp.conf"):
    config = configparser.ConfigParser(inline_comment_prefixes="#")     # allow inline comments
    if config_file not in config.read(config_file):   # reading file failed
        raise FileNotFoundError(errno.ENOENT, "failed to read config file", config_file)

    if file_path != "":     # ignore if file is stdin
        file_path = os.path.abspath(file_path)  # prevent multiple calls to os.path.abspath for cache handler

    request_order=config.get("request", "request_order", fallback="GET POST COOKIE").split()
    keep_blank_values=config.getboolean("request", "keep_blank_values", fallback=True)
    fallback_value=config.get("request", "fallback_value", fallback="")
    enable_post_data_reading=config.getboolean("request", "enable_post_data_reading", fallback=False)
    default_mimetype=config.get("request", "default_mimetype", fallback="text/html")
    PyHP = libpyhp.PyHP(    # init PyHP object
            file_path=file_path,
            request_order=request_order,
            keep_blank_values=keep_blank_values,
            fallback_value=fallback_value,
            enable_post_data_reading=enable_post_data_reading,
            default_mimetype=default_mimetype,
        )
    libpyhp.setup_environment(PyHP)

    # handle caching
    regex = config.get("parser", "regex", fallback="\\<\\?pyhp[\\s](.*?)[\\s]\\?\\>").encode("utf8").decode("unicode_escape")  # process escape sequences like \n
    caching_enabled = config.getboolean("caching", "enable", fallback=True)
    caching_allowed = config.getboolean("caching", "auto", fallback=False)
    # if file is not stdin and caching is enabled and wanted or auto_caching is enabled
    if check_if_caching(file_path, caching, caching_enabled, caching_allowed):
        handler_path = prepare_path(config.get("caching", "handler_path", fallback="/usr/lib/pyhp/cache_handlers/files_mtime.py"))  # get neccesary data
        cache_path = config.get("caching", "path", fallback="~/.pyhp/cache")    # do not use prepare_path because cache_path may be used for configuration
        max_size = config.getint("caching", "max_size", fallback=16)
        ttl = config.getint("caching", "ttl", fallback=-1)
        handler = import_path(handler_path).Handler(cache_path, max_size, ttl)    # init handler
        try:
            if not handler.is_available(file_path): # assert(handler.is_available(file_path)) could be removed when optimized
                raise RuntimeError  # handler failed or caching not possible
        except: # load file without cache
            code = embed.FromString(prepare_file(file_path), regex)
            code.execute(embed.python_execute, userdata=[{"PyHP": PyHP}, 0])
        else:   # handler successful
            PyHP.set_cache_handler(handler) # enable cache functions
            if handler.is_outdated(file_path):  # update cache
                code = embed.FromString(prepare_file(file_path), regex)
                code.process(embed.python_compile, userdata=[file_path, 0]) # compile code sections
                handler.save(file_path, code.sections)  # save preprocessed code
            else:
                code = embed.FromIter(handler.load(file_path))  # load cache
            code.execute(embed.python_execute_compiled, userdata=[{"PyHP": PyHP}, 0])
        finally:
            handler.shutdown()  # shutdown handler
    else:   # same as except clause
        code = embed.FromString(prepare_file(file_path), regex)
        code.execute(embed.python_execute, userdata=[{"PyHP": PyHP}, 0])

    if not PyHP.headers_sent():  # prevent error if no output occured, but not if an exception occured
        PyHP.send_headers()
    return 0    # return 0 on success

# prepare path for use
def prepare_path(path):
    return os.path.expanduser(path)

# import file at path
def import_path(path):
    sys.path.insert(0, os.path.dirname(path))   # modify module search path
    path = os.path.splitext(os.path.basename(path))[0]  # get filename without .py
    path = importlib.import_module(path)    # import module
    del sys.path[0]  # cleanup module search path
    return path

# check we should cache
def check_if_caching(file_path, caching, enabled, auto):
    possible = file_path != ""  # file is not stdin
    allowed = (caching or auto) and enabled    # if caching is wanted and enabled
    return possible and allowed

# get code and remove shebang
def prepare_file(path):
    if path == "":
        code = sys.stdin.read()
    else:
        with open(path, "r") as fd:
            code = fd.read()
    if code.startswith("#!"):   # remove shebang
        code = code.partition("\n")[2]  # get all lines except the first line
    return code
