#!/usr/bin/python3

"""Tests for pyhp.wsgi.proxys"""

import unittest
import unittest.mock
import io
import threading
from pyhp.wsgi import proxys


class Dummy:
    pass


class TestLocalStackProxy(unittest.TestCase):
    """test LocalStackProxy"""

    def test_eq(self) -> None:
        """test LocalStackProxy.__eq__"""
        p = [
            proxys.LocalStackProxy(1),
            proxys.LocalStackProxy(2),
            proxys.LocalStackProxy(1)
        ]
        p[2].push(1)
        for proxy in p:
            self.assertEqual([obj for obj in p if obj == proxy], [proxy])
        self.assertNotEqual(p[0], 42)

    def test_attr(self) -> None:
        """test attribute access"""
        default = Dummy()
        default.x = 0
        proxy = proxys.LocalStackProxy(default)
        self.assertEqual(proxy.x, 0)
        proxy.x = 1
        self.assertEqual(proxy.x, 1)
        self.assertEqual(default.x, 1)
        del proxy.x
        with self.assertRaises(AttributeError):
            proxy.x
        with self.assertRaises(AttributeError):
            default.x

    def test_stack(self) -> None:
        """test stack"""
        dummies = [
            Dummy(),
            Dummy()
        ]
        proxy = proxys.LocalStackProxy(dummies[0])
        self.assertIs(proxy.peek(), dummies[0])
        proxy.push(dummies[1])
        self.assertIs(proxy.peek(), dummies[1])
        self.assertIs(proxy.pop(), dummies[1])
        self.assertIs(proxy.peek(), dummies[0])

    def test_replace(self) -> None:
        """test LocalStackProxy.replace"""
        dummies = [
            Dummy(),
            Dummy()
        ]
        proxy = proxys.LocalStackProxy(dummies[0])
        with proxy.replace(dummies[1]) as obj:
            self.assertIs(obj, dummies[1])
            self.assertIs(proxy.peek(), dummies[1])
        self.assertIs(proxy.peek(), dummies[0])

    def test_local(self) -> None:
        """test LocalStackProxy local-ness"""
        dummies = [
            Dummy(),
            Dummy()
        ]
        proxy = proxys.LocalStackProxy(dummies[0])
        thread = threading.Thread(target=lambda: proxy.push(dummies[1]))
        thread.start()
        thread.join()
        self.assertIs(proxy.peek(), dummies[0])
