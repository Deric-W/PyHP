#!/usr/bin/python3

"""Dummy for testing PathHierarchyBuilder"""

import sys

sys.path.append("../../")
try:
    from pyhp.backends.memory import HashMap
finally:
    sys.path.pop()
