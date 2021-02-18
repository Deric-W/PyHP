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
import re
import argparse
from contextlib import ExitStack
from typing import Any, Mapping, Iterable, MutableMapping
import toml
from . import __version__, libpyhp
from .compiler import util, generic, parsers
from .caching import CodeSourceContainer
from .caching.util import ModuleHierarchyBuilder, PathHierarchyBuilder


__all__ = (
    "CONFIG_LOCATIONS",
    "argparser",
    "cli_main",
    "main",
    "load_config"
)

CONFIG_LOCATIONS = (
    os.path.expanduser("~/.config/pyhp.toml"),
    "/etc/pyhp.toml"
)

argparser = argparse.ArgumentParser(
    prog="pyhp",
    description="Interpreter for .pyhp Scripts (https://github.com/Deric-W/PyHP)"
)
argparser.add_argument(
    "-v",
    "--version",
    help="display version number",
    action="version",
    version=f"%(prog)s {__version__}"
)
argparser.add_argument(
    "-c",
    "--config",
    type=str,
    help="path to custom config file",
    default=None
)
argparser.add_argument(
    "name",
    type=str,
    help="name to be loaded from the caching hierarchy (omit for reading from stdin)",
    nargs="?",
    default="-"
)


def cli_main() -> int:
    """cli entry point"""
    args = argparser.parse_args()
    if args.config is None:     # try to find the config location
        config = load_config()
    else:                       # user specified the config location
        config = toml.load(args.config)
    return main(args.name, config)


def main(name: str, config: Mapping[str, Any]) -> int:
    """start the PyHP Interpreter with predefined arguments"""
    # prepare compiler
    parser = parsers.RegexParser(
        re.compile(config["parser"]["start"]),
        re.compile(config["parser"]["end"])
    )
    builder = generic.GenericCodeBuilder(
        config["compiler"]["optimization_level"]
    )
    compiler = util.Compiler(
        parser,
        util.Dedenter(builder) if config["compiler"]["dedent"] else builder
    )

    with ExitStack() as exit_stack:
        if name == "-":  # read from stdin
            code = compiler.compile_file(sys.stdin)
        else:
            container = exit_stack.enter_context(
                get_container(compiler, config["caching"])
            )
            code = exit_stack.enter_context(container[name]).code()

        # prepare the PyHP Object
        PyHP = get_pyhp(name, config["request"])

        exit_stack.push(reset_stdout)
        # prevent universal newlines from messing with text sections
        sys.stdout.reconfigure(newline="\n")    # type: ignore
        # wrap stdout
        sys.stdout.write = PyHP.make_header_wrapper(sys.stdout.write)   # type: ignore
        try:
            for text in code.execute({"PyHP": PyHP}):
                sys.stdout.write(text)
        finally:    # run shutdown functions even if a exception occurred
            PyHP.run_shutdown_functions()
        if not PyHP.headers_sent():  # send headers manually if no output or error occurred
            PyHP.send_headers()
    return 0    # return 0 on success


def load_config(search_paths: Iterable[str] = CONFIG_LOCATIONS) -> MutableMapping[str, Any]:
    """locate and parse the config file"""
    try:
        path = os.environ["PYHPCONFIG"]
    except KeyError:
        pass
    else:
        return toml.load(path)
    for path in search_paths:
        try:
            return toml.load(path)
        except FileNotFoundError:
            pass
    raise RuntimeError("failed to locate the config file")


def get_container(compiler: util.Compiler, caching_config: Mapping[str, Any]) -> CodeSourceContainer:
    """create a code source container from config data"""
    resolve = caching_config["resolve"]
    if resolve == "module":
        hierarchy_builder = ModuleHierarchyBuilder(compiler)
    elif resolve == "path":
        hierarchy_builder = PathHierarchyBuilder(compiler)  # type: ignore
    else:
        raise ValueError(f"value '{resolve}' of key 'resolve' is unknown")
    hierarchy_builder.add_config(caching_config["containers"])
    return hierarchy_builder.hierarchy()


def get_pyhp(name: str, request_config: Mapping[str, Any]) -> libpyhp.PyHP:
    """create a PyHP instance from config data"""
    return libpyhp.PyHP(
        file_path=name,
        request_order=request_config["request_order"],
        keep_blank_values=request_config["keep_blank_values"],
        fallback_value=request_config.get("fallback_value", ""),
        enable_post_data_reading=request_config["enable_post_data_reading"],
        default_mimetype=request_config["default_mimetype"]
    )


def reset_stdout(*_args: Any) -> bool:
    """reset stdout"""
    sys.stdout.reconfigure(newline=None)    # type: ignore
    return False    # dont swallow exceptions
