#!/usr/bin/python3

"""Module for handling pyhp files"""

import os.path
from sys import stdout


class CompileError(ValueError, SyntaxError):
    """Exception raised if compiling a section fails"""
    pass


class Code:
    """class representing a compiled code string"""
    __slots__ = "sections"

    def __init__(self, sections):
        self.sections = tuple(sections)

    def execute(self, globals, locals):
        """execute code sections with the given globals and locals"""
        for section, is_code in self.iter_sections():
            if is_code:
                exec(section, globals, locals)
            elif section:
                stdout.write(section)
            else:   # ignore empty sections
                pass

    def iter_sections(self):
        """generator yielding every section with a bool indicating if the section is code"""
        is_code = False
        for section in self.sections:
            yield section, is_code
            is_code = not is_code


def get_indentation(line):
    """get indentation of a line of python code"""
    indentation = ""
    for char in line:
        if char.isspace():
            indentation += char
        else:
            break   # reached end of identation
    return indentation

def dedent_section(file, offset, section):
    """remove a starting indentation from a code section"""
    lines = section.splitlines()
    indentation = None
    for line_num, line in enumerate(lines):
        if not (not line or line.isspace() or line.lstrip().startswith("#")):  # ignore lines without code
            if indentation is None:             # first line of code, set starting indentation
                indentation = get_indentation(line)
            if line.startswith(indentation):    # if line starts with starting indentation
                lines[line_num] = line[len(indentation):]  # remove starting indentation
            else:
                raise IndentationError(
                    "indentation not matching",
                    (file, line_num + offset + 1, len(indentation), line)
                    )  # raise Exception on bad indentation
    return "\n".join(lines) # join the lines back together

class Parser:
    """class implementing a parser for pyhp files"""
    def __init__(self, start, end, dedent=True, optimization_level=-1):
        """
        init with compiled regex for section start and end,
        if code section should be dedented and optimization level for compile()
        """
        self.start = start
        self.end = end
        self.code_steps = [dedent_section] if dedent else []
        self.text_steps = []
        self.optimization_level = optimization_level

    def parse(self, string, line_offset=0):
        """iterator yielding the sections of str with their line offsets, beginning with a text section"""
        pos = 0
        length = len(string)
        is_code = False
        while pos < length:
            match = self.end.search(string, pos) if is_code else self.start.search(string, pos)   # search for the end if we are in a code section, otherwise for the next code section
            if match is None:   # if we are still in this loop we are not at the end
                yield line_offset, string[pos:]
                break
            else:
                yield line_offset, string[pos:match.start()]
                line_offset += string.count("\n", pos, match.end())
                pos = match.end()
                is_code = not is_code   # toggle mode
    
    def process(self, string, file="<string>", line_offset=0):
        """iterator yielding the processed code sections"""
        steps = self.text_steps
        for offset, section in self.parse(string, line_offset=line_offset):
            for step in steps:
                section = step(file, offset, section)
            if steps is self.code_steps:
                try:
                    section = compile(section, file, "exec", optimize=self.optimization_level)
                except Exception as err:
                    raise CompileError("Exception while compiling code section") from err
                else:
                    yield section   # Python >= 3.8 --> section.replace(co_firstlineno=section.co_firstlineno + offset)   # set correct first line number
                steps = self.text_steps
            else:
                yield section
                steps = self.code_steps
    
    def compile_string(self, string, file="<string>", line_offset=0):
        """compile string into Code object"""
        return Code(self.process(string, file, line_offset))
    
    def compile_file(self, fd, line_offset=0):
        """compile file descriptor into Code object and strip shebang"""
        first_line = fd.readline()
        if first_line.startswith("#!"):  # shebang
            code = fd.read()    # ignore first line
            line_offset += 1    # increment offset because we removed the shebang
        else:
            code = first_line + fd.read()
        return Code(self.process(code, fd.name, line_offset))


class CacheManager:
    """implementation of the caching system"""
    def __init__(self, parser, *cache_handlers, ignore_errors=False):
        """init with parser, cache handlers and if cache errors should be ignored"""
        self.parser = parser
        self.cache_handlers = cache_handlers
        self.ignore_errors = ignore_errors

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.shutdown()
        return False    # we dont handle exceptions
    
    def caching_enabled(self):
        """return if caching is enabled"""
        return len(self.cache_handlers) > 0

    def load(self, file_path):
        """load file from disk or cache and renew cache if needed"""
        file_path = os.path.abspath(file_path)
        renew_stack = []    # stack containing outdated caches
        for cache_handler in self.cache_handlers:   # try all caches starting with first one
            try:
                code = Code(cache_handler.load(file_path))
            except cache_handler.renew_exceptions:  # cache outdated, push on stack and continue
                renew_stack.append(cache_handler)
            except Exception:
                if self.ignore_errors:  # ignore exception
                    renew_stack.append(cache_handler)
                else:
                    raise
            else:   # valid cache found, exit loop
                break
        else:   # no valid cache was found, load code from disk
            with open(file_path, "r") as fd:
                code = self.parser.compile_file(fd)
        for cache_handler in renew_stack:   # update all outdated caches
            try:
                cache_handler.save(file_path, code.sections)
            except Exception:
                if not self.ignore_errors:  # ignore exception if ignore_errors = True
                    raise
        return code

    def cache(self, file_path):
        """cache file in top level cache"""
        file_path = os.path.abspath(file_path)
        with open(file_path, "r") as fd:
            code = self.parser.compile_file(fd)
        self.cache_handlers[0].save(file_path, code.sections)

    def is_outdated(self, file_path):
        """check if cached file is outdated"""
        return self.cache_handlers[0].is_outdated(os.path.abspath(file_path))

    def invalidate(self, file_path, force=False):
        """remove cached file from all caches if it is outdated or force = True"""
        file_path = os.path.abspath(file_path)
        for cache_handler in self.cache_handlers:
            if force or cache_handler.is_outdated(file_path):
                cache_handler.remove(file_path)

    def reset(self):
        """remove all caches"""
        for cache_handler in self.cache_handlers:
            cache_handler.reset()

    def shutdown(self):
        """shutdown cache handlers"""
        for cache_handler in self.cache_handlers:
            cache_handler.shutdown()
