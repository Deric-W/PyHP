#!/usr/bin/python3

# Module for processing strings embedded in text files, preferably Python code.
# This module is part of PyHP (https://github.com/Deric-W/PyHP)
"""Module for processing strings embedded in text files"""

import re
import sys
from io import StringIO
from contextlib import redirect_stdout

__all__ = ["FromString", "FromIter", "python_execute", "python_compile", "python_execute_compiled", "python_align", "python_get_indentation", "python_is_comment"]

# class for handling strings
class FromString:
    # get string, regex to isolate code and optional flags for the regex (default for processing text files)
    # the userdata is given to the processor function to allow state
    def __init__(self, string, regex, flags=re.MULTILINE|re.DOTALL, userdata=None):
        self.sections = re.split(regex, string, flags=flags)
        self.userdata = userdata

    # process string with the code replaced by the output of the processor function
    # this will modify self.sections
    def process(self, processor):
        code_sections = 0
        # the first section is always not code, and every code section has string sections as neighbors
        for i in range(1, len(self.sections), 2):
            code_sections += 1
            self.sections[i] = processor(self.sections[i], self.userdata)
        return code_sections

    # process the string and write the string and replaced code parts to sys.stdout
    # this will not modify self.sections an requires an processor to write the data himself
    def execute(self, processor):
        code_sections = 0
        for i in range(0, len(self.sections)):
            code_sections += 1
            if i % 2 == 1:  # uneven index --> code
                processor(self.sections[i], self.userdata)
            else:           # even index --> not code
                if self.sections[i]:    # ignore empthy sections
                    sys.stdout.write(self.sections[i])
        return code_sections

    def __str__(self):
        return "".join(self.sections)


# wrapper class for handling presplit strings
class FromIter(FromString):
    # get presplit string as iterator
    def __init__(self, iterator, userdata=None):
        self.sections = list(iterator) 
        self.userdata = userdata        


# function for executing python code
# userdata = [locals, section_number], init with [{}, 0]
def python_execute(code, userdata):
    userdata[1] += 1
    try:
        exec(python_align(code), globals(), userdata[0])
    except Exception as e:  # tell the user the section of the Exception
        raise Exception("Exception during execution of section %d" % userdata[1]) from e

# compile python code sections
# userdata = [file, section_number], init with [str, 0]
def python_compile(code, userdata):
    userdata[1] += 1
    try:
        return compile(python_align(code), userdata[0], "exec") 
    except Exception as e:  # tell the user the section of the Exception
        raise Exception("Exception during executing of section %d" % userdata[1]) from e

# execute compiled python sections
# userdata is the same as python_execute
def python_execute_compiled(code, userdata):
    userdata[1] += 1
    try:
        exec(code, globals(), userdata[0])
    except Exception as e:
        raise Exception("Exception during executing of section %d" % userdata[1]) from e

# function for aligning python code in case of a startindentation
def python_align(code, indentation=None):
    line_num = 0
    code = code.split("\n")     # split to lines
    for line in code:
        line_num += 1
        if not (not line or line.isspace() or python_is_comment(line)): # ignore non code lines
            if indentation == None:     # first line of code, get startindentation
                indentation = python_get_indentation(line)
            if line.startswith(indentation): # if line starts with startindentation
                code[line_num - 1] = line[len(indentation):]  # remove startindentation
            else:
                raise IndentationError("File: code processed by python_align Line: %d" % line_num)  # raise Exception on bad indentation
    return "\n".join(code)  # join the lines back together
                    

# function for getting the indentation of a line of python code
def python_get_indentation(line):
    indentation = ""
    for char in line:
        if char in " \t":
            indentation += char
        else:
            break
    return indentation

# check if complete line is a comment
def python_is_comment(line):
    return line.strip(" \t").startswith("#")
