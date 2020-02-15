#!/usr/bin/python3
# format stdin with cli arguments
import sys

data = sys.stdin.read()
data = data.format(*sys.argv[1:])
sys.stdout.write(data)
