#!/usr/bin/python3

"""Module containing functions for the pyhp-backends command"""
# The backends.main module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

import sys
import re
import pickle
from argparse import ArgumentParser, FileType, Namespace
from typing import Callable, Union, Optional, Tuple, List, Iterable, TextIO
import toml
from .. import __version__
from ..config import load_config
from ..compiler import parsers, util
from . import CodeSourceContainer, CodeSource, TimestampedCodeSource
from .caches import CacheSource, CacheSourceContainer
from .util import hierarchy_from_config

__all__ = (
    "main",
    "argparser"
)


def cache_subcommand(function: Callable[[CacheSourceContainer[CodeSourceContainer, CacheSource], Namespace, TextIO], int]) -> Callable[[CodeSourceContainer[CodeSource], Namespace, TextIO], int]:
    """helper which filters backends for subcommands which require a cache"""
    def wrapper(backend: CodeSourceContainer[CodeSource], args: Namespace, stdout: TextIO = sys.stdout) -> int:
        if isinstance(backend, CacheSourceContainer):
            return function(backend, args, stdout)
        print("Error: backend is not a cache", file=sys.stderr)
        return 3    # to distinguish between exceptions and wrong backends
    return wrapper


@cache_subcommand
def main_fetch(backend: CacheSourceContainer[CodeSourceContainer, CacheSource], args: Namespace, _: TextIO = sys.stdout) -> int:
    """implementation of the fetch subcommand"""
    for name in args.names:
        with backend[name] as source:
            source.fetch()
    return 0


@cache_subcommand
def main_gc(backend: CacheSourceContainer[CodeSourceContainer, CacheSource], args: Namespace, stdout: TextIO = sys.stdout) -> int:
    """implementation of the gc subcommand"""
    if len(args.names) == 0:
        print(f"Collected {backend.gc()} names", file=stdout)
    else:
        for name in args.names:
            with backend[name] as source:
                if source.gc():
                    print(f"Collected '{name}'", file=stdout)
    return 0


@cache_subcommand
def main_clear(backend: CacheSourceContainer[CodeSourceContainer, CacheSource], args: Namespace, _: TextIO = sys.stdout) -> int:
    """implementation of the clear subcommand"""
    if len(args.names) == 0:
        backend.clear()
    else:
        for name in args.names:
            with backend[name] as source:
                source.clear()
    return 0


def main_list(backend: CodeSourceContainer[CodeSource], args: Namespace, stdout: TextIO = sys.stdout) -> int:
    """implementation of the list subcommand"""
    if isinstance(backend, CacheSourceContainer):
        cached_mapping = backend.cached()
        if args.cached:
            iterator = cached_mapping.keys()    # type: Iterable[str]
            cached = lambda name: True
        else:
            iterator = backend.keys()
            cached = lambda name: name in cached_mapping
    else:
        cached = lambda name: False
        if args.cached:
            iterator = []
        else:
            iterator = backend.keys()
    if args.pattern is not None:
        pattern = re.compile(args.pattern)
        iterator = filter(pattern.fullmatch, iterator)
    for name in iterator:
        if cached(name):
            print(f"'{name}' [cached]", file=stdout)
        else:
            print(f"'{name}'", file=stdout)
    return 0


def main_show(backend: CodeSourceContainer[CodeSource], args: Namespace, stdout: TextIO = sys.stdout) -> int:
    """implementation of the show subcommand"""
    with backend[args.name] as source:
        if isinstance(source, TimestampedCodeSource):
            mtime, ctime, atime = source.info()     # type: Tuple[Union[str, int], Union[str, int], Union[str, int]]
        else:
            mtime = ctime = atime = "Not supported"
        if isinstance(source, CacheSource):
            cached = source.cached()    # type: Union[str, bool]
        else:
            cached = "Not supported"
        print(f"Name: '{args.name}'", file=stdout)
        print(f"mtime: {mtime}", file=stdout)
        print(f"ctime: {ctime}", file=stdout)
        print(f"atime: {atime}", file=stdout)
        print(f"cached: {cached}", file=stdout)
    return 0


def main_dump(backend: CodeSourceContainer[CodeSource], args: Namespace, _: TextIO = sys.stdout) -> int:
    """implementation of the dump subcommand"""
    with backend[args.name] as source:
        pickle.dump(source.code(), args.output, protocol=args.protocol)
    return 0


argparser = ArgumentParser(
    description="Command to interact with PyHP backends (https://github.com/Deric-W/PyHP)"
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
    nargs="?",
    default=None,
    help="path to custom config file"
)

# not setting dest triggers an error when the subcommand is missing from the cli
subcommands = argparser.add_subparsers(required=True, dest="subcommand")
list_parser = subcommands.add_parser(
    "list",
    description="list the names provided by the backend",
    help="list the names provided by the backend"
)
list_parser.add_argument(
    "pattern",
    type=str,
    nargs="?",
    default=None,
    help="regex to filter names, defaults to no filtering"
)
list_parser.add_argument(
    "-c",
    "--cached",
    action="store_true",
    help="just list names which are cached"
)
list_parser.set_defaults(function=main_list)

show_parser = subcommands.add_parser(
    "show",
    description="show details about a name",
    help="show details about a name"
)
show_parser.add_argument(
    "name",
    type=str,
    help="name to show details about"
)
show_parser.set_defaults(function=main_show)

fetch_parser = subcommands.add_parser(
    "fetch",
    description="warm the cache",
    help="warm the cache"
)
fetch_parser.add_argument(
    "names",
    type=str,
    nargs="+",
    help="names to load in the cache"
)
fetch_parser.set_defaults(function=main_fetch)

clear_parser = subcommands.add_parser(
    "clear",
    description="clear the cache",
    help="clear the cache"
)
clear_parser.add_argument(
    "names",
    type=str,
    nargs="*",
    help="names to remove, defaults to all names"
)
clear_parser.set_defaults(function=main_clear)

gc_parser = subcommands.add_parser(
    "gc",
    description="garbage collect the cache",
    help="garbage collect the cache"
)
gc_parser.add_argument(
    "names",
    type=str,
    nargs="*",
    help="name to collect, defaults to all names"
)
gc_parser.set_defaults(function=main_gc)

dump_parser = subcommands.add_parser(
    "dump",
    description="dump names from the backend",
    help="dump names from the backend"
)
dump_parser.add_argument(
    "name",
    type=str,
    help="name to dump"
)
dump_parser.add_argument(
    "-o",
    "--output",
    type=FileType("wb"),
    default=sys.stdout.buffer,
    help="file to write the content to"
)
dump_parser.add_argument(
    "-p",
    "--protocol",
    type=int,
    default=pickle.DEFAULT_PROTOCOL,
    help="pickle protocol to use, defaults to pickle.DEFAULT_PROTOCOL"
)
dump_parser.set_defaults(function=main_dump)


def main(argv: Optional[List[str]] = None, stdout: TextIO = sys.stdout) -> int:
    """cli entry point"""
    args = argparser.parse_args(argv)   # behaves differently when argv == sys.argv
    if args.config is None:
        config = load_config()
    else:
        config = toml.load(args.config)
    compiler = util.Compiler.from_config(
        parsers.RegexParser.from_config(config.get("parser", {})),
        config.get("compiler", {})
    )
    with hierarchy_from_config(compiler, config.get("backend", {})) as backend:
        return args.function(backend, args, stdout)
