#!/usr/bin/python3

"""Module containing the main function(s) of the PyHP Interpreter"""
# This module is part of PyHP (https://github.com/Deric-W/PyHP)

from . import embed
from . import libpyhp

__all__ = ["main", "manual_main"]

# start the PyHP Interpreter
def main():
    pass

# start the PyHP Interpreter with predefined arguments
def manual_main(file, caching=False, config="/etc/pyhp.conf"):
    pass