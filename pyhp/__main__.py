#!/usr/bin/python3

# script to support python3 -m pyhp

import sys
from .main import main, get_args

# get cli arguments
args = get_args()

# execute main with file_path as normal argument and the rest as keyword arguments
sys.exit(main(args.pop("file_path"), **args))
