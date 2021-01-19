#!/usr/bin/python3

"""Module containing the main function(s) of the PyHP Interpreter"""
# The main module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

import sys
import os
import argparse
import configparser
import importlib
import atexit
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

    # prepare the PyHP Object
    PyHP = libpyhp.PyHP(file_path=file_path,
                        request_order=config.get("request", "request_order", fallback="GET POST COOKIE").split(),
                        keep_blank_values=config.getboolean("request", "keep_blank_values", fallback=True),
                        fallback_value=config.get("request", "fallback_value", fallback=""),
                        enable_post_data_reading=config.getboolean("request", "enable_post_data_reading", fallback=False),
                        default_mimetype=config.get("request", "default_mimetype", fallback="text/html")
                        )
    sys.stdout.write = PyHP.make_header_wrapper(sys.stdout.write)  # wrap stdout
    atexit.register(PyHP.run_shutdown_functions)    # run shutdown functions even if a exception occured

    # handle caching
    regex = config.get("parser", "regex", fallback="\\<\\?pyhp[\\s](.*?)[\\s]\\?\\>").encode("utf8").decode("unicode_escape")  # process escape sequences like \n
    caching_enabled = config.getboolean("caching", "enable", fallback=True)
    caching_allowed = config.getboolean("caching", "auto", fallback=False)
    # if file is not stdin and caching is enabled and wanted or auto_caching is enabled
    if check_if_caching(file_path, caching, caching_enabled, caching_allowed):
        handler_path = prepare_path(config.get("caching", "handler_path", fallback="/lib/pyhp/cache_handlers/files_mtime.py"))  # get neccesary data
        cache_path = prepare_path(config.get("caching", "path", fallback="~/.pyhp/cache"))
        handler = import_path(handler_path)
        handler = handler.Handler(cache_path, os.path.abspath(file_path), config["caching"])    # init handler
        if handler.is_available():  # check if caching is possible
            cached = True
            if handler.is_outdated():   # update cache
                code = embed.FromString(prepare_file(file_path), regex, userdata=[file_path, 0])  # set userdata for python_compile
                code.process(embed.python_compile)  # compile python sections
                code.userdata = [{"PyHP": PyHP}, 0]  # set userdata for python_execute_compiled
                handler.save(code.sections)     # just save the code sections
            else:   # load cache
                code = embed.FromIter(handler.load(), userdata=[{"PyHP": PyHP}, 0])
        else:   # generate FromString Object
            cached = False
            code = embed.FromString(prepare_file(file_path), regex, userdata=[{"PyHP": PyHP}, 0])
        handler.close()
    else:   # same as above
        cached = False
        code = embed.FromString(prepare_file(file_path), regex, userdata=[{"PyHP": PyHP}, 0])

    if cached:  # run compiled code
        code.execute(embed.python_execute_compiled)
    else:   # run normal code
        code.execute(embed.python_execute)

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
