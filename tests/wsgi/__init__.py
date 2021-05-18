#!/usr/bin/python3

"""Tests for pyhp.wsgi"""

import unittest
import unittest.mock
from pyhp import wsgi


class TestFunctions(unittest.TestCase):
    """tests for stand-alone functions"""

    def test_map_failsafe(self) -> None:
        """test map_failsafe"""
        files = [
            unittest.mock.Mock(),
            unittest.mock.Mock(),
            unittest.mock.Mock(),
            unittest.mock.Mock()
        ]
        files[1].close.configure_mock(side_effect=RuntimeError)
        files[2].close.configure_mock(side_effect=ValueError)
        try:
            wsgi.map_failsafe(lambda f: f.close(), files)
        except ValueError as e:
            self.assertIsInstance(e.__context__, RuntimeError)
        for mock in files:
            mock.close.assert_called()
        files.clear()
        wsgi.map_failsafe(lambda f: f.close(), files)
