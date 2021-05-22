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
from wsgiref.handlers import CGIHandler
from typing import Any, Iterable, MutableMapping
import toml
from . import __version__
from .wsgi.apps import SimpleWSGIApp
from .wsgi.util import SimpleWSGIAppFactory
from .backends.memory import MemorySource


__all__ = (
    "CONFIG_LOCATIONS",
    "argparser",
    "cli_main",
    "cgi_main",
    "load_config"
)

CONFIG_LOCATIONS = (
    os.path.expanduser("~/.config/pyhp.toml"),
    "/etc/pyhp.toml"
)

argparser = argparse.ArgumentParser(
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
    help="name to be loaded from the backend (omit for reading from stdin)",
    nargs="?",
    default="-"
)
argparser.add_argument(
    "args",
    help="Arguments passed to the script in cli mode",
    nargs=argparse.REMAINDER
)


class CLIHandler(CGIHandler):
    """subclass of CGIHandler that adds SCRIPT_FILENAME, argv and argc and drops headers"""
    __slots__ = ()

    def __init__(self, args: argparse.Namespace) -> None:
        CGIHandler.__init__(self)
        if args.name != "-":    # ignore if reading from sys.stdin
            self.base_env["SCRIPT_FILENAME"] = args.name
        self.base_env["argv"] = [args.name] + args.args
        self.base_env["argc"] = len(args.args) + 1  # type: ignore

    def send_headers(self) -> None:
        """drop headers in cli mode"""
        pass

    def handle_error(self) -> None:
        """log current error but do not send special error output in cli mode"""
        self.log_exception(sys.exc_info())


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


def cli_main() -> int:
    """cli entry point"""
    args = argparser.parse_args()
    if args.config is None:     # try to find the config location
        config = load_config()
    else:                       # user specified the config location
        config = toml.load(args.config)
    with SimpleWSGIAppFactory.from_config(config) as factory:
        if args.name == "-":    # read from stdin
            app = SimpleWSGIApp(
                MemorySource(factory.compiler.compile_str(
                    sys.stdin.read(),
                    sys.stdin.name
                )),     # sys.stdin has no location
                factory.interface_factory
            )
        else:   # use the backend of the factory
            app = factory.app(args.name)
        with app:
            CLIHandler(args).run(app)   # type: ignore
    return 0


def cgi_main() -> int:
    """cgi entry point"""
    args = argparser.parse_args()
    if args.config is None:     # try to find the config location
        config = load_config()
    else:                       # user specified the config location
        config = toml.load(args.config)
    with SimpleWSGIAppFactory.from_config(config) as factory:
        if args.name == "-":    # read from stdin
            app = SimpleWSGIApp(
                MemorySource(factory.compiler.compile_str(
                    sys.stdin.read(),
                    sys.stdin.name
                )),     # sys.stdin has no location
                factory.interface_factory
            )
        else:   # use the backend of the factory
            app = factory.app(args.name)
        with app:
            CGIHandler().run(app)   # type: ignore
    return 0
