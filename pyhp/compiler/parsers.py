#!/usr/bin/python3

"""Module containing parsers"""
# The compiler.parsers module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from typing import Pattern, Tuple, Iterator
from . import Parser


class RegexParser(Parser):
    """parser implementation identifying the start and end of a section with regular expressions"""
    __slots__ = ("start", "end")

    start: Pattern[str]

    end: Pattern[str]

    def __init__(self, start: Pattern[str], end: Pattern[str]) -> None:
        """construct a instance with the patterns for the start and end of code sections"""
        self.start = start
        self.end = end

    def parse(self, source: str) -> Iterator[Tuple[str, int, bool]]:
        """parse source code, yielding sections with line offset and bool to indicate if they are code"""
        pos = 0
        offset = 0
        length = len(source)
        is_code = False                 # start with text section because code sections start after self.start
        while pos < length:             # finish parsing if we reached the end of the source
            if is_code:                 # search for the end if we are in a code section
                match = self.end.search(source, pos)
            else:                       # otherwise for the next code section
                match = self.start.search(source, pos)
            if match is None:           # current section is the last one, yield rest of source
                yield source[pos:], offset, is_code
                break                   # no match left in source, finish parsing
            else:
                yield source[pos:match.start()], offset, is_code
                offset += source.count("\n", pos, match.end())  # update offset
                pos = match.end()       # update pos to end of match
                is_code = not is_code   # toggle mode, codes comes after text and so on
