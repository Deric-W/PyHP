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
import os.path
import re
import argparse
import configparser
import importlib
from typing import TextIO, Any
from . import __version__, libpyhp
from .compiler import util, generic, parsers


__all__ = ("argparser", "main")

argparser = argparse.ArgumentParser(
    prog="pyhp",
    description="Interpreter for .pyhp Scripts (https://github.com/Deric-W/PyHP)"
)
argparser.add_argument(
    "-c", "--caching",
    help="enable caching (requires file)",
    action="store_true"
)
argparser.add_argument(
    "-v", "--version",
    help="display version number",
    action="version",
    version=f"%(prog)s {__version__}"
)
argparser.add_argument(
    "file", type=argparse.FileType('r'),
    help="file to be interpreted (omit for reading from stdin)",
    nargs="?",
    default=sys.stdin
)
argparser.add_argument(
    "--config",
    type=str,
    help="path to custom config file",
    default="/etc/pyhp.conf"
)


def main(file: TextIO, caching: bool = False, config_file: str = "/etc/pyhp.conf") -> int:
    """start the PyHP Interpreter with predefined arguments"""
    config = configparser.ConfigParser(inline_comment_prefixes="#")     # allow inline comments
    with open(config_file, "r") as fd:
        config.read_file(fd)

    # prepare the PyHP Object
    PyHP = libpyhp.PyHP(
        file_path=file.name,
        request_order=config.get("request", "request_order", fallback="GET POST COOKIE").split(),
        keep_blank_values=config.getboolean("request", "keep_blank_values", fallback=True),
        fallback_value=config.get("request", "fallback_value", fallback=""),
        enable_post_data_reading=config.getboolean("request", "enable_post_data_reading", fallback=False),
        default_mimetype=config.get("request", "default_mimetype", fallback="text/html")
    )
    # wrap stdout
    sys.stdout.write = PyHP.make_header_wrapper(sys.stdout.write)   # type: ignore

    # prepare compiler
    parser = parsers.RegexParser(
        re.compile(
            config.get(
                "parser",
                "start",
                fallback=r"<\?pyhp\s"
            ).encode("utf8").decode("unicode_escape")   # process escape sequences like \n
        ),
        re.compile(
            config.get(
                "parser",
                "end",
                fallback=r"\s\?>"
            ).encode("utf8").decode("unicode_escape")   # process escape sequences like \n
        )
    )
    builder = generic.GenericCodeBuilder(
        config.getint("compiler", "optimization_level", fallback=-1)
    )
    compiler = util.Compiler(
        parser,
        util.Dedenter(builder) if config.getboolean("parser", "dedent", fallback=True) else builder
    )

    # handle caching
    caching_enabled = config.getboolean("caching", "enable", fallback=True)
    caching_allowed = config.getboolean("caching", "auto", fallback=False)
    # if file is not stdin and caching is enabled and wanted or auto_caching is enabled
    if check_if_caching(file, caching, caching_enabled, caching_allowed):
        handler_path = config.get(
            "caching",
            "handler_path",
            fallback="/lib/pyhp/cache_handlers/files_mtime.py"
        )  # get neccesary data
        cache_path = prepare_path(config.get("caching", "path", fallback="~/.pyhp/cache"))
        handler = import_path(handler_path)
        with handler.Handler(cache_path, os.path.abspath(file.name), config["caching"]) as handler:
            if handler.is_available():  # check if caching is possible
                if handler.is_outdated():   # update cache
                    code = compiler.compile_file(file)
                    handler.save(code)
                else:   # load cache
                    code = handler.load()
            else:
                code = compiler.compile_file(file)
    else:
        code = compiler.compile_file(file)

    try:
        for text in code.execute({"PyHP": PyHP}):
            sys.stdout.write(text)
    finally:    # run shutdown functions even if a exception occured
        PyHP.run_shutdown_functions()

    if not PyHP.headers_sent():  # prevent error if no output occured, but not if an exception occured
        PyHP.send_headers()
    return 0    # return 0 on success


def prepare_path(path: str) -> str:
    """prepare path for use"""
    return os.path.expanduser(path)


def import_path(path: str) -> Any:
    """import file at path"""
    sys.path.insert(0, os.path.dirname(path))   # modify module search path
    path = os.path.splitext(os.path.basename(path))[0]  # get filename without .py
    module = importlib.import_module(path)    # import module
    del sys.path[0]  # cleanup module search path
    return module


def check_if_caching(file: TextIO, caching: bool, enabled: bool, auto: bool) -> bool:
    """check if we should cache"""
    possible = file != sys.stdin
    allowed = (caching or auto) and enabled    # if caching is wanted and enabled
    return possible and allowed
