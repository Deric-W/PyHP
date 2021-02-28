#!/usr/bin/python3

"""Module containing utilities"""
# The caching.util module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations
from abc import ABCMeta, abstractmethod
import importlib
import importlib.util
from typing import List, Sequence, Mapping, Type, TypeVar, Any, Union
from . import CodeSourceContainer, CodeSource
from ..compiler.util import Compiler


__all__ = (
    "HierarchyBuilder",
    "ConfigHierarchyBuilder",
    "ModuleHierarchyBuilder",
    "PathHierarchyBuilder"
)

T = TypeVar("T", bound="HierarchyBuilder")


class HierarchyBuilder:
    """Class used to build a hierarchy of CodeSourceContainers"""
    __slots__ = ("containers", "compiler", "__weakref__")

    containers: List[CodeSourceContainer[CodeSource]]

    compiler: Compiler

    def __init__(self, compiler: Compiler) -> None:
        self.containers = []
        self.compiler = compiler

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HierarchyBuilder):
            return self.containers == other.containers \
                and self.compiler == other.compiler
        return NotImplemented

    def add_container(self, container: Type[CodeSourceContainer], config: Mapping[str, Any]) -> None:
        """add a CodeSourceContainer to the hierarchy"""
        try:    # decorator
            before = self.containers[-1]    # type: Union[CodeSourceContainer, Compiler]
        except IndexError:  # first container
            before = self.compiler
        self.containers.append(container.from_config(config, before))

    def hierarchy(self) -> CodeSourceContainer[CodeSource]:
        """retrieve the hierarchy"""
        return self.containers[-1]

    def pop(self) -> CodeSourceContainer:
        """remove and return the top container from the hierarchy"""
        return self.containers.pop()

    def copy(self: T) -> T:
        """copy the builder with his current state"""
        builder = self.__class__.__new__(self.__class__)
        builder.containers = self.containers.copy()
        builder.compiler = self.compiler
        return builder


class ConfigHierarchyBuilder(HierarchyBuilder, metaclass=ABCMeta):
    """Hierarchy builder used to build hierarchies from config files"""
    __slots__ = ()

    def add_config(self, containers: Sequence[Mapping[str, Any]]) -> None:
        """add containers defined in parsed config data"""
        for container in containers:
            name = container["name"]
            if isinstance(name, str):
                config = container["config"]
                if isinstance(config, Mapping):
                    self.add_name(name, config)
                else:
                    raise ValueError("value of key 'config' expected to be a Mapping")
            else:
                raise ValueError("value of key 'name' expected to be a str")

    @abstractmethod
    def add_name(self, name: str, config: Mapping[str, Any]) -> None:
        """add a CodeSourceContainer to the hierarchy by name"""
        raise NotImplementedError


class ModuleHierarchyBuilder(ConfigHierarchyBuilder):
    """ConfigHierarchyBuilder which treats names as module names"""
    __slots__ = ()

    def add_name(self, name: str, config: Mapping[str, Any]) -> None:
        """add a CodeSourceContainer to the hierarchy by module name"""
        module, _, name = name.rpartition(".")
        container = getattr(importlib.import_module(module), name)
        self.add_container(container, config)


class PathHierarchyBuilder(ConfigHierarchyBuilder):
    """ConfigHierarchyBuilder which treats names as file paths"""
    __slots__ = ()

    def add_name(self, name: str, config: Mapping[str, Any]) -> None:
        """add a CodeSourceContainer to the hierarchy by file path and name seperated by ':'"""
        path, _, name = name.rpartition(":")
        spec = importlib.util.spec_from_file_location("container_module", location=path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)     # type: ignore
        self.add_container(getattr(module, name), config)
