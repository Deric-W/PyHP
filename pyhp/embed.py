#!/usr/bin/python3

# Module for processing strings embedded in text files, preferably Python code.
# This module is part of PyHP (https://github.com/Deric-W/PyHP)
"""Module for processing strings embedded in text files"""

import re
import sys


class FromString:
    """class for processing sections inside files"""
    # get string, regex to isolate code and optional flags for the regex (default for processing text files)
    def __init__(self, string, regex, flags=re.MULTILINE | re.DOTALL):
        self.sections = re.split(regex, string, flags=flags)

    # the userdata is given to the processor function to allow state
    # this will modify self.sections
    def process(self, processor, userdata=None):
        """process code sections with processor function"""
        code_sections = 0
        # the first section is always not code, and every code section has string sections as neighbors
        for i in range(1, len(self.sections), 2):
            code_sections += 1
            self.sections[i] = processor(self.sections[i], userdata)
        return code_sections

    # the userdata is given to the processor function to allow state
    # this will not modify self.sections an requires an processor to write the data himself
    def execute(self, processor, userdata=None):
        """process code sections and write sections to stdout"""
        code_sections = 0
        for i in range(0, len(self.sections)):
            code_sections += 1
            if i % 2 == 1:  # uneven index --> code
                processor(self.sections[i], userdata)
            else:           # even index --> not code
                if self.sections[i]:    # ignore empthy sections
                    sys.stdout.write(self.sections[i])
        return code_sections

    def __str__(self):
        return "".join(self.sections)


class FromIter(FromString):
    """class for handling presplit strings"""
    # get presplit string as iterator
    def __init__(self, iterator):
        self.sections = list(iterator)

# userdata = [locals, section_number], init with [{}, 0]
def python_execute(code, userdata):
    """execute python code sections"""
    userdata[1] += 1
    try:
        exec(python_align(code), globals(), userdata[0])
    except Exception as e:  # tell the user the section of the Exception
        raise Exception("Exception during execution of section %d" % userdata[1]) from e

# userdata = [file, section_number], init with [str, 0]
def python_compile(code, userdata):
    """compile python code sections"""
    userdata[1] += 1
    try:
        return compile(python_align(code), userdata[0], "exec")
    except Exception as e:  # tell the user the section of the Exception
        raise Exception("Exception during executing of section %d" % userdata[1]) from e

# userdata is the same as python_execute
def python_execute_compiled(code, userdata):
    """execute compiled python code sections"""
    userdata[1] += 1
    try:
        exec(code, globals(), userdata[0])
    except Exception as e:
        raise Exception("Exception during executing of section %d" % userdata[1]) from e

# function for aligning python code in case of a startindentation
def python_align(code, indentation=None):
    """removes initial indentation from python code sections"""
    line_num = 0
    code = code.splitlines()     # split to lines
    for line in code:
        line_num += 1
        if not (not line or line.isspace() or is_comment(line)):  # ignore non code lines
            if indentation is None:     # first line of code, get startindentation
                indentation = get_indentation(line)
            if line.startswith(indentation):  # if line starts with startindentation
                code[line_num - 1] = line[len(indentation):]  # remove startindentation
            else:
                raise IndentationError("indentation not matching", ("embedded code section", line_num, len(indentation), line))  # raise Exception on bad indentation
    return "\n".join(code)  # join the lines back together


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
