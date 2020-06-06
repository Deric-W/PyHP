#!/usr/bin/python3

"""Module for handling pyhp files"""

import sys
import os.path


class CompileError(ValueError, SyntaxError):
    """Exception raised if compiling a section fails"""
    pass


class Code:
    """class representing a parsed code string"""
    __slots__ = "sections"

    def __init__(self, sections):
        self.sections = [section for section in sections]

    def execute(self, globals, locals):
        """execute code sections with the given globals and locals"""
        for index, section in enumerate(self.sections):
            if index % 2 != 0:  # uneven index --> code
                try:
                    exec(section, globals, locals)
                except Exception as err:    # tell the user the section of the Exception
                    raise RuntimeError("Exception during execution of section {0}".format(index // 2)) from err
            elif section:       # even index --> not code
                sys.stdout.write(section)
            else:   # ignore empty sections
                pass

    def compile(self, file="<string>", optimize=-1):
        """compile code sections"""
        # the first section is always not code, and every code section has string sections as neighbors
        for index in range(1, len(self.sections), 2):
            try:
                self.sections[index] = compile(self.sections[index], file, "exec", optimize=optimize)
            except Exception as err:    # tell the user the section of the Exception
                raise CompileError("Exception during compilation of section {0}".format(index // 2)) from err

    def iter_sections(self):
        """generator yielding every section with a bool indicating if the section is code"""
        for index, section in enumerate(self.sections):
            yield section, index % 2 != 0


class RawParser:
    """class implementing a parser for pyhp files with raw code sections"""
    def __init__(self, start, end):
        """init with compiled start regex, end regex"""
        self.start = start
        self.end = end
    
    def parse_sections(self, string):
        """iterator yielding the sections of str, beginning with non code section"""
        pos = 0
        length = len(string)
        is_code = False
        while pos < length:
            match = self.end.search(string, pos) if is_code else self.start.search(string, pos)   # search for the end if we are in a code section, otherwise for the next code section
            if match is None:   # if we are still in this loop we are not at the end
                yield string[pos:]
                break
            else:
                yield string[pos:match.start()]
                pos = match.end()
                is_code = not is_code   # toggle mode

    def parse(self, string):
        """create code object from string"""
        return Code(self.parse_sections(string))


def get_indentation(line):
    """get indentation of a line of python code"""
    indentation = ""
    for char in line:
        if char.isspace():
            indentation += char
        else:
            break   # reached end of identation
    return indentation

class DedentParser(RawParser):
    """parser for pyhp files with indented code sections"""
    def dedent(self, sections, start_indent=None):
        """iterator removing a starting indentation from code sections"""
        for index, section in enumerate(sections):
            if index % 2 != 0:  # code section
                indentation = start_indent
                line_num = 0
                lines = section.splitlines()
                for line in lines:
                    line_num += 1
                    if not (not line or line.isspace() or line.lstrip().startswith("#")):  # ignore lines without code
                        if indentation is None:             # first line of code, set starting indentation
                            indentation = get_indentation(line)
                        if line.startswith(indentation):    # if line starts with starting indentation
                            lines[line_num - 1] = line[len(indentation):]  # remove starting indentation
                        else:
                            raise IndentationError(
                                "indentation not matching",
                                ("code section {0}".format(index // 2), line_num, len(indentation), line)
                            )  # raise Exception on bad indentation
                yield "\n".join(lines) # join the lines back together
            else:   # not code, dont change
                yield section

    def parse(self, string):
        """create code object from string with dedented code sections"""
        return Code(self.dedent(self.parse_sections(string)))


def strip_shebang(code):
    """strip shebang from code"""
    return code.partition("\n")[2] if code.startswith("#!") else code   # return all lines except the first line if the first line is a shebang


class FileLoader:
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

    def _get_code(self, file_path):
        """get code object from file"""
        with open(file_path, "r") as fd:
            return self.parser.parse(strip_shebang(fd.read()))
    
    def caching_enabled(self):
        """return if caching is enabled"""
        return len(self.cache_handlers) != 0

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
            code = self._get_code(file_path)
            code.compile(file=file_path)
        for cache_handler in renew_stack:   # update all outdated caches
            try:
                cache_handler.save(file_path, code.sections)
            except Exception:
                if not self.ignore_errors:  # ignore exception if ignore_errors = True
                    raise
        return code

    def cache(self, file_path):
        """cache file in top level cache"""
        code = self._get_code(file_path)
        code.compile(file=file_path)
        self.cache_handlers[0].save(os.path.abspath(file_path), code)

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
        """shutdown cache handler"""
        for cache_handler in self.cache_handlers:
            cache_handler.shutdown()
