#!/usr/bin/python3

"""Package for embedding and using python code like php"""

# package metadata
# needs to be defined before .main is imported
__version__ = "2.0"
__author__ = "Eric Wolf"
__maintainer__ = "Eric Wolf"
__license__ = "MIT"
__email__ = "robo-eric@gmx.de"  # please dont use for spam :(
__contact__ = "https://github.com/Deric-W/PyHP"

# import all submodules
from . import embed
from . import libpyhp
from . import main
