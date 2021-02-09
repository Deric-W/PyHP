#!/usr/bin/python3

"""Dummy for testing PathHierarchyBuilder"""

import sys

sys.path.append("../../")
try:
    from pyhp.caching.memory import MemorySourceContainer
finally:
    sys.path.pop()
