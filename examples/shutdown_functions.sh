#!/bin/sh -e
# script for testing register_shutdown_function

cd shutdown_functions
pyhp register_shutdown_function.pyhp|diff register_shutdown_function.output -
cd ..
