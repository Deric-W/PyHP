#!/usr/bin/python3

"""Module for handling pyhp files"""

import sys

class Code:
    """Class implementing pyhp files"""
    def __init__(self, data, regex):
        """
        init with data and compiled regex to split data into sections.
        If regex is None data will not be split.
        """
        if regex is None:
            self.sections = list(data)
        else:
            self.sections = regex.split(data)
    
    def execute(self, globals, locals):
        """execute code sections with the given globals and locals"""
        code_section = 0
        for i in range(len(self.sections)):
            if i % 2 != 0:  # uneven index --> code
                code_section += 1
                try:
                    exec(self.sections[i], globals, locals)
                except Exception as err:    # tell the user the section of the Exception
                    raise RuntimeError("Exception during execution of section {0}".format(code_section)) from err
            else:           # even index --> not code
                if self.sections[i]:    # ignore empthy sections
                    sys.stdout.write(self.sections[i])
    

    def compile(self, file="<string>", optimize=-1):
        """compile code sections"""
        code_section = 0
        # the first section is always not code, and every code section has string sections as neighbors
        for i in range(1, len(self.sections), 2):
            code_section += 1
            try:
                self.sections[i] = compile(self.sections[i], file, "exec", optimize=optimize)
            except Exception as err:    # tell the user the section of the Exception
                raise RuntimeError("Exception during compilation of section {0}".format(code_section)) from err

    def dedent(self, indentation=None):
        """remove starting indentation from code sections"""
        code_section = 0
        for i in range(1, len(self.sections), 2):
            start_indent = indentation
            code_section += 1
            line_num = 0
            lines = self.sections[i].splitlines()   # split code into lines
            for line in lines:
                line_num += 1
                if not (not line or line.isspace() or is_comment(line)):  # ignore non code lines
                    if start_indent is None:     # first line of code, set starting indentation
                        start_indent = get_indentation(line)
                    if line.startswith(start_indent):  # if line starts with starting indentation
                        lines[line_num - 1] = line[len(start_indent):]  # remove starting indentation
                    else:
                        raise IndentationError("indentation not matching", ("code section {0}".format(code_section), line_num, len(start_indent), line))  # raise Exception on bad indentation
            self.sections[i] = "\n".join(lines) # join the lines back together

    def get_sections(self):
        """get file sections"""
        return self.sections


def get_indentation(line):
    """get indentation of a line of python code"""
    indentation = ""
    for char in line:
        if char in " \t":
            indentation += char
        else:
            break
    return indentation

def is_comment(line):
    """check if line of python code is a comment"""
    return line.lstrip().startswith("#")
