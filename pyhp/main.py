#!/usr/bin/python3

"""Module containing the main function(s) of the PyHP Interpreter"""
# This module is part of PyHP (https://github.com/Deric-W/PyHP)

import sys
import os.path
import re
from argparse import ArgumentParser
from configparser import ConfigParser
from importlib.util import spec_from_file_location, module_from_spec
from . import __version__
from .embed import Parser, CacheManager
from .libpyhp import PyHP


def get_args():
    """get cli arguments for main as dict"""
    parser = ArgumentParser(prog="pyhp", description="Interpreter for .pyhp Scripts (https://github.com/Deric-W/PyHP)")
    parser.add_argument("-c", "--caching", help="enable caching (requires file)", action="store_true")
    parser.add_argument("-v", "--version", help="display version number", action="version", version="%(prog)s {version}".format(version=__version__))
    parser.add_argument("file", type=str, help="file to be interpreted (omit for reading from stdin)", nargs="?", default=None)
    parser.add_argument("--config", type=str, help="path to custom config file", nargs="?", const="/etc/pyhp.conf", default="/etc/pyhp.conf")
    args = parser.parse_args()
    return {"file_path": args.file, "caching": args.caching, "config_file": args.config}

# import file from path
def import_path(path):
    spec = spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)    # create spec with file name without extension as name
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def init_handlers(handlers):
    """init cache handlers from iterator yielding handlers and arguments as strings"""
    return [import_path(handler).Handler(location, float(max_size), float(ttl)) for handler, location, max_size, ttl in handlers]

def main(file_path, caching=False, config_file="/etc/pyhp.conf"):
    """start the PyHP Interpreter with predefined arguments"""
    # create config obj
    config = ConfigParser(inline_comment_prefixes=("#", ";"))  # allow inline comments
    with open(config_file, "r") as fd:
        config.read_file(fd, source=config_file)
    # create pyhp obj
    request_order=config.get("request", "request_order", fallback="GET POST COOKIE").split()
    keep_blank_values=config.getboolean("request", "keep_blank_values", fallback=True)
    fallback_value=config.get("request", "fallback_value", fallback="")
    enable_post_data_reading=config.getboolean("request", "enable_post_data_reading", fallback=False)
    default_mimetype=config.get("request", "default_mimetype", fallback="text/html")
    pyhp = PyHP(    # init PyHP object
        file_path=sys.argv[0] if file_path is None else file_path,
        request_order=request_order,
        keep_blank_values=keep_blank_values,
        fallback_value=fallback_value,
        enable_post_data_reading=enable_post_data_reading,
        default_mimetype=default_mimetype
    )
    # create parser
    start = config.get("parser", "start", fallback="<\\?pyhp\\s").encode("utf8").decode("unicode_escape")  # process escape sequences like \n
    end = config.get("parser", "end", fallback="\\s\\?>").encode("utf8").decode("unicode_escape")  # process escape sequences like \n
    dedent = config.getboolean("parser", "dedent", fallback=True)
    optimization_level = config.getint("parser", "optimization_level", fallback=-1)
    parser = Parser(
        re.compile(start),
        re.compile(end),
        dedent=dedent,
        optimization_level=optimization_level
    )
    # create cache manager
    enabled = config.getboolean("caching", "enable", fallback=True)
    forced = config.getboolean("caching", "auto", fallback=False)
    ignore_errors = config.getboolean("caching", "ignore_errors", fallback=False)
    handlers = zip(
        config.get("caching", "handler_paths", fallback="/usr/lib/pyhp/cache_handlers/files_mtime.py").split(),
        config.get("caching", "locations", fallback="~/.cache/pyhp").split(),
        config.get("caching", "max_sizes", fallback="16").split(),
        config.get("caching", "ttls", fallback="-1").split(),
    )
    cache = CacheManager(
        parser,
        *init_handlers(handlers) if enabled and (caching or forced) else [],
        ignore_errors=ignore_errors
    )
    # setup and execute
    with cache, pyhp:
        pyhp.cache_set_handler(cache, False)   # cache shutdown is handled by context manager
        sys.stdout.write = pyhp.make_header_wrapper(sys.stdout.write)   # make headers be send if output occurs
        sys.stdout.writelines = pyhp.make_header_wrapper(sys.stdout.writelines)
        if file_path is None:
            code = parser.compile_file(sys.stdin)
        else:
            code = cache.load(file_path)
        code.execute(globals(), {"PyHP": pyhp})
    return 0
