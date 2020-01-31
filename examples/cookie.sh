#!/bin/sh -e
# script for testing the cookie functions

cd cookie
pyhp setrawcookie.pyhp|diff setrawcookie.output -
pyhp setcookie.pyhp|diff setcookie.output -
cd ..
