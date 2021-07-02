#!/usr/bin/python3

"""format stdin with cli arguments"""

import sys


sys.stdout.write(
    sys.stdin.read().format(*sys.argv[1:])
)
