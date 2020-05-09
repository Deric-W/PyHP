#!/usr/bin/python3

"""Module for handling pyhp files"""

import sys
import os.path


class CompileError(ValueError, SyntaxError):
    """Exception raised if compiling a section fails"""
    pass


class Code:
    """Class implementing pyhp files"""
    def __init__(self, data, regex=None, dedent=False):
        """
        init with data and compiled regex to split data into sections.
        If regex is None data will not be split.
        If dedent is True the code sections will have their starting indentation removed.
        """
        if regex is None:
            self.sections = list(data)
        else:
            self.sections = regex.split(data)
        if dedent:
            self.dedent()

    def execute(self, globals, locals):
        """execute code sections with the given globals and locals"""
        code_section = 0
        for index, section in enumerate(self.sections):
            if index % 2 != 0:  # uneven index --> code
                code_section += 1
                try:
                    exec(section, globals, locals)
                except Exception as err:    # tell the user the section of the Exception
                    raise RuntimeError("Exception during execution of section {0}".format(code_section)) from err
            else:           # even index --> not code
                if section:    # ignore empthy sections
                    sys.stdout.write(section)

    def compile(self, file="<string>", optimize=-1):
        """compile code sections"""
        code_section = 0
        # the first section is always not code, and every code section has string sections as neighbors
        for i in range(1, len(self.sections), 2):
            code_section += 1
            try:
                self.sections[i] = compile(self.sections[i], file, "exec", optimize=optimize)
            except Exception as err:    # tell the user the section of the Exception
                raise CompileError("Exception during compilation of section {0}".format(code_section)) from err

    def dedent(self, start_indent=None):
        """remove starting indentation from code sections"""
        code_section = 0
        for i in range(1, len(self.sections), 2):
            indentation = start_indent
            code_section += 1
            line_num = 0
            lines = self.sections[i].splitlines()   # split code into lines
            for line in lines:
                line_num += 1
                if not (not line or line.isspace() or is_comment(line)):  # ignore non code lines
                    if indentation is None:     # first line of code, set starting indentation
                        indentation = get_indentation(line)
                    if line.startswith(indentation):  # if line starts with starting indentation
                        lines[line_num - 1] = line[len(indentation):]  # remove starting indentation
                    else:
                        raise IndentationError("indentation not matching", ("code section {0}".format(code_section), line_num, len(indentation), line))  # raise Exception on bad indentation
            self.sections[i] = "\n".join(lines) # join the lines back together

    def iter_sections(self):
        """generator yielding every section with a bool indicating if the section is code"""
        for index, section in enumerate(self.sections):
            yield section, index % 2 != 0


class CacheExceptionHandler:
    """Context manager for handling exceptions during caching"""
    code = None

    def __init__(self, ignore_errors):
        self.ignore_errors = ignore_errors

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if type in (CompileError, IndentationError):    # code may be messed up
            self.code = None
        return self.ignore_errors   # reraise exception if ignore_errors is False, suppress otherwise


class FileLoader:
    """implementation of the caching system"""
    def __init__(self, cache_handler=None, regex=None, dedent=False, ignore_errors=False):
        """init with cache handler, compiled regex to split code sections, if the code should be dedented and if cache errors should be ignored"""
        self.cache_handler = cache_handler
        self.regex = regex
        self.dedent = dedent
        self.ignore_errors = ignore_errors

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.shutdown()
        return False    # we dont handle exceptions

    def _from_file(self, file_path):
        """get code object from file"""
        with open(file_path, "r") as fd:
            return Code(strip_shebang(fd.read()), self.regex, dedent=self.dedent)
    
    def _from_stream(self, stream):
        """get code object from stream"""
        return Code(strip_shebang(stream.read()), self.regex, dedent=self.dedent)
    
    def caching_enabled(self):
        """return if caching is enabled"""
        return self.cache_handler is not None

    def load(self, file_path):
        """load file from stream, disk or cache and renew cache if needed"""
        if hasattr(file_path, "read"):  # load from stream
            return self._from_stream(file_path)
        elif self.cache_handler is None:  # load directly from disk
            return self._from_file(file_path)
        else:   # use cache
            file_path = os.path.abspath(file_path)
            with CacheExceptionHandler(self.ignore_errors) as exception_handler:
                try:
                    exception_handler.code = Code(self.cache_handler.load(file_path))
                except self.cache_handler.renew_exceptions:
                    exception_handler.code = self._from_file(file_path)
                    exception_handler.code.compile(file=file_path)
                    self.cache_handler.save(file_path, exception_handler.code.sections)
            return self._from_file(file_path) if exception_handler.code is None else exception_handler.code  # generate new code object if it was not already generated

    def cache(self, file_path):
        """cache file"""
        code = self._from_file(file_path)
        code.compile(file_path)
        self.cache_handler.save(os.path.abspath(file_path), code.sections)

    def is_outdated(self, file_path):
        """check if cached file is outdated"""
        return self.cache_handler.is_outdated(os.path.abspath(file_path))

    def invalidate(self, file_path, force=False):
        """remove cached file from the cache if it is outdated or force = True"""
        file_path = os.path.abspath(file_path)
        if force or self.cache_handler.is_outdated(file_path):
            self.cache_handler.remove(file_path)

    def reset(self):
        """remove entire cache"""
        self.cache_handler.reset()

    def shutdown(self):
        """shutdown cache handler"""
        if self.cache_handler is not None:
            self.cache_handler.shutdown()


def get_indentation(line):
    """get indentation of a line of python code"""
    indentation = ""
    for char in line:
        if char in " \t":
            indentation += char
        else:
            break   # reached end of identation
    return indentation

def is_comment(line):
    """check if a line of python code is a comment"""
    return line.lstrip().startswith("#")    # check if first 'normal' character is a '#'

def strip_shebang(code):
    """strip shebang from code"""
    if code.startswith("#!"):
        code = code.partition("\n")[2]  # return all lines except the first line
    return code
