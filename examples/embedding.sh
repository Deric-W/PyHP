#!/bin/sh -e
# script for testing the embedding features

cd embedding
pyhp syntax.pyhp|diff syntax.output -
pyhp shebang.pyhp|diff shebang.output -
pyhp indentation.pyhp|diff indentation.output -
cd ..
