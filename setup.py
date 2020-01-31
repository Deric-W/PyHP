#!/usr/bin/python3

import setuptools
import pyhp

with open("README.md", "r") as fd:
    long_description = fd.read()

setuptools.setup(
    name="pyhp-core",   # pyhp was already taken
    license="LICENSE",
    version=pyhp.__version__,
    author=pyhp.__author__,
    author_email=pyhp.__email__,
    description="package for embedding and using python code like php",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=pyhp.__contact__,
    packages=["pyhp"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires='>=3.5',
)
