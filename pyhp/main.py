#!/usr/bin/python3

"""Module containing the main function(s) of the PyHP Interpreter"""
# This module is part of PyHP (https://github.com/Deric-W/PyHP)

import sys
import os
import argparse
import configparser
import errno
import re
import importlib.util
from . import __version__
from .embed import FileLoader
from .libpyhp import PyHP

__all__ = ["get_args", "main"]

def get_args():
    """get cli arguments for main as dict"""
    parser = argparse.ArgumentParser(prog="pyhp", description="Interpreter for .pyhp Scripts (https://github.com/Deric-W/PyHP)")
    parser.add_argument("-c", "--caching", help="enable caching (requires file)", action="store_true")
    parser.add_argument("-v", "--version", help="display version number", action="version", version="%(prog)s {version}".format(version=__version__))
    parser.add_argument("file", type=str, help="file to be interpreted (omit for reading from stdin)", nargs="?", default=sys.stdin)
    parser.add_argument("--config", type=str, help="path to custom config file", nargs="?", const="/etc/pyhp.conf", default="/etc/pyhp.conf")
    args = parser.parse_args()
    return {"file_path": args.file, "caching": args.caching, "config_file": args.config}

def main(file_path, caching=False, config_file="/etc/pyhp.conf"):
    """start the PyHP Interpreter with predefined arguments"""
    # create config obj
    config = configparser.ConfigParser(inline_comment_prefixes="#")     # allow inline comments
    if config_file not in config.read(config_file):   # reading file failed
        raise FileNotFoundError(errno.ENOENT, "failed to read config file", config_file)
    # create pyhp obj
    request_order=config.get("request", "request_order", fallback="GET POST COOKIE").split()
    keep_blank_values=config.getboolean("request", "keep_blank_values", fallback=True)
    fallback_value=config.get("request", "fallback_value", fallback="")
    enable_post_data_reading=config.getboolean("request", "enable_post_data_reading", fallback=False)
    default_mimetype=config.get("request", "default_mimetype", fallback="text/html")
    pyhp = PyHP(    # init PyHP object
            file_path=sys.argv[0] if file_path is sys.stdin else file_path,
            request_order=request_order,
            keep_blank_values=keep_blank_values,
            fallback_value=fallback_value,
            enable_post_data_reading=enable_post_data_reading,
            default_mimetype=default_mimetype
        )
    # create loader obj
    regex = config.get("parser", "regex", fallback="\\<\\?pyhp[\\s](.*?)[\\s]\\?\\>").encode("utf8").decode("unicode_escape")  # process escape sequences like \n
    regex = re.compile(regex, flags=re.MULTILINE | re.DOTALL)
    dedent = config.getboolean("parser", "dedent", fallback=True)
    ignore_errors = config.getboolean("caching", "ignore_errors", fallback=False)
    caching_enabled = config.getboolean("caching", "enable", fallback=True)
    caching_forced = config.getboolean("caching", "auto", fallback=False)
    handler_path = config.get("caching", "handler_path", fallback="/usr/lib/pyhp/cache_handlers/files_mtime.py")
    location = config.get("caching", "location", fallback="~/.cache/pyhp")
    max_size = config.getfloat("caching", "max_size", fallback=16.0)
    ttl = config.getfloat("caching", "ttl", fallback=-1)
    loader = FileLoader(
            import_path(handler_path).Handler(location, max_size, ttl) if (caching_forced or caching) and caching_enabled else None,
            regex,
            dedent,
            ignore_errors
        )
    # setup and execute
    with loader, pyhp:
        pyhp.cache_set_handler(loader, False)   # loader shutdown is handled by context manager
        code = loader.load(file_path)
        sys.stdout.write = pyhp.make_header_wrapper(sys.stdout.write)   # make headers be send if output occures
        sys.stdout.writelines = pyhp.make_header_wrapper(sys.stdout.writelines)
        code.execute(globals(), {"PyHP": pyhp})
    return 0

# prepare path for use
def prepare_path(path):
    return os.path.expanduser(path)

# import file from path
def import_path(path):
    spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)    # create spec with file name without extension as name
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
