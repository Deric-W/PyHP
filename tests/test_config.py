#!/usr/bin/python3

"""Unit tests for pyhp.config"""

import os
import unittest
import toml
from pyhp import config


class TestFunctions(unittest.TestCase):
    """test free functions"""

    def test_load_config(self) -> None:
        """test load_config"""
        with self.assertRaises(RuntimeError):   # no config
            config.load_config()
        os.environ["PYHPCONFIG"] = "pyhp.toml"  # env var
        try:
            self.assertEqual(config.load_config(), toml.load("pyhp.toml"))
        finally:
            del os.environ["PYHPCONFIG"]
        self.assertEqual(                       # search path
            config.load_config(("test1", "test2", "pyhp.toml")),
            toml.load("pyhp.toml")
        )
