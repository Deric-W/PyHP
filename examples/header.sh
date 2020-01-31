#!/bin/sh -e
# script for testing the header features

cd header
pyhp header.pyhp|diff header.output -
pyhp headers_list.pyhp|diff headers_list.output -
pyhp header_remove.pyhp|diff header_remove.output -
pyhp headers_sent.pyhp|diff headers_sent.output -
pyhp header_register_callback.pyhp|diff header_register_callback.output -
cd ..
