#!/bin/sh -e
# script for testing the caching features

test -f /lib/pyhp/cache_handlers/files_mtime.py
test ! -f ~/.cache/pyhp/$(pwd)/embedding/syntax.pyhp.cache
pyhp --caching embedding/syntax.pyhp|diff embedding/syntax.output -
test -f ~/.cache/pyhp/$(pwd)/embedding/syntax.pyhp.cache
pyhp --caching embedding/syntax.pyhp|diff embedding/syntax.output -
