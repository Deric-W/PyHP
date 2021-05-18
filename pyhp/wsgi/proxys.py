#!/usr/bin/python3

"""Module containing proxys for capturing output"""
# The proxys module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

import threading
from abc import abstractmethod, ABCMeta
from typing import TypeVar, ContextManager, Any, Generic, Optional, Type, Deque
from types import TracebackType

__all__ = (
    "StackProxy",
    "LocalStackProxy"
)

T = TypeVar("T")


class StackProxy(Generic[T], metaclass=ABCMeta):
    """stack like object proxy"""
    __slots__ = ("__weakref__",)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.peek(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self.peek(), name, value)

    def __delattr__(self, name: str) -> None:
        delattr(self.peek(), name)

    @abstractmethod
    def peek(self) -> T:
        """return the current target"""
        raise NotImplementedError

    @abstractmethod
    def push(self, replacement: T) -> None:
        """add a new target"""
        raise NotImplementedError

    @abstractmethod
    def pop(self) -> T:
        """remove and return the current target"""
        raise NotImplementedError

    def replace(self, replacement: T) -> ContextManager[T]:
        """return a context manager in which the current target is replaced"""
        return StackProxyContext(self, replacement)


class StackProxyContext(ContextManager[T]):
    """StackProxy context manager"""
    __slots__ = ("proxy", "replacement")

    proxy: StackProxy[T]

    replacement: T

    def __init__(self, proxy: StackProxy[T], replacement: T) -> None:
        self.proxy = proxy
        self.replacement = replacement

    def __enter__(self) -> T:
        self.proxy.push(self.replacement)
        return self.replacement

    def __exit__(self, type: Optional[Type[BaseException]], value: Optional[BaseException], traceback: Optional[TracebackType]) -> bool:    # type: ignore
        self.proxy.pop()
        return False


class LocalStackProxyInner(threading.local, Generic[T]):
    """container containing the local stacks for each thread"""

    stack: Deque[T]

    def __init__(self, default: T) -> None:
        self.stack = Deque((default,))


class LocalStackProxy(StackProxy[T]):
    """implementation with different targets for each thread"""
    __slots__ = ("inner",)

    inner: LocalStackProxyInner[T]

    def __init__(self, default: T) -> None:
        object.__setattr__(self, "inner", LocalStackProxyInner(default))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LocalStackProxy):
            return self.inner.stack == other.inner.stack
        return NotImplemented

    def peek(self) -> T:
        """return the current target"""
        return self.inner.stack[-1]

    def push(self, replacement: T) -> None:
        """add a new target"""
        return self.inner.stack.append(replacement)

    def pop(self) -> T:
        """remove and return the current target"""
        return self.inner.stack.pop()
