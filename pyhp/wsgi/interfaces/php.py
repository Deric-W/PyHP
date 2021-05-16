#!/usr/bin/python3

"""Module containing a PHP-style interface"""
# The php module is part of PyHP (https://github.com/Deric-W/PyHP)
# Copyright (C) 2021  Eric Wolf

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-only

# the many type: ignore comments are caused by https://github.com/python/mypy/issues/5485

from __future__ import annotations
import os
import time
import urllib.parse
from tempfile import gettempdir
from http import HTTPStatus
from wsgiref.headers import Headers
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Tuple,
    Union,
    Mapping,
    Sequence
)
import werkzeug.http
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.datastructures import MultiDict
from werkzeug.formparser import parse_form_data
from ...backends.caches import CacheSourceContainer
from .. import Environ, StartResponse
from . import WSGIInterface, WSGIInterfaceFactory
from .phputils import (
    valid_path,
    SimpleCallbackQueue,
    ArgumentCallbackQueue,
    FilesType,
    StreamFactory,
    UploadStreamFactory,
    NullStreamFactory
)

__all__ = (
    "close_files",
    "PHPWSGIInterface",
    "PHPWSGIInterfaceFactory"
)


def close_files(iterator: Iterable[Any]) -> None:
    """close a iterable of objects with a .close method"""
    previous_exception = None
    for file in iterator:
        try:
            file.close()
        except Exception as e:  # dont stop when .close fails
            e.__context__ = previous_exception
            previous_exception = e
    if previous_exception is not None:
        raise previous_exception


def unquote_cookie(cookie: Tuple[str, str]) -> Tuple[str, str]:
    """unquote a (name, value) pair"""
    return urllib.parse.unquote(cookie[0]), urllib.parse.unquote(cookie[1])


class UnquotingMultiDict(MultiDict):
    """subclass of MultiDict[str, str] which unquotes keys and values when passed an iterable"""
    __slots__ = ()

    def __init__(
        self,
        mapping: Optional[Union[Mapping[str, Union[str, Iterable[str]]], Iterable[Tuple[str, str]]]] = None
    ):
        if mapping is None or isinstance(mapping, Mapping):
            super().__init__(mapping)
        else:
            super().__init__(map(unquote_cookie, mapping))


class PHPWSGIInterface(WSGIInterface):
    """PHP-style interface implementation"""
    __slots__ = (
        "status_code",
        "headers",
        "header_sent",
        "header_callbacks",
        "cache",
        "shutdown_callbacks",
        "SERVER",
        "REQUEST",
        "GET",
        "POST",
        "FILES",
        "COOKIE"
    )

    status_code: int

    headers: Headers

    header_sent: bool

    header_callbacks: SimpleCallbackQueue

    cache: CacheSourceContainer

    shutdown_callbacks: ArgumentCallbackQueue

    SERVER: MutableMapping[str, Any]

    REQUEST: MultiDict[str, str]

    GET: MultiDict[str, str]

    POST: MultiDict[str, str]

    FILES: MultiDict[str, FilesType]

    COOKIE: MultiDict[str, str]

    def __init__(
        self,
        environ: Environ,
        start_response: StartResponse,
        status_code: int,
        headers: Headers,
        cache: CacheSourceContainer,
        request_order: Iterable[str] = ("GET", "POST", "COOKIE"),
        post_max_size: Optional[int] = None,
        stream_factory: Optional[StreamFactory] = None
    ) -> None:
        self.environ = environ
        self.SERVER = self.create_server()
        self.start_response = start_response    # type: ignore
        self.status_code = status_code
        self.headers = headers
        self.header_sent = False
        self.header_callbacks = SimpleCallbackQueue()
        self.cache = cache
        self.shutdown_callbacks = ArgumentCallbackQueue()
        self.GET = self.create_get()
        self.COOKIE = self.create_cookie()
        self.POST, self.FILES = self.create_post(post_max_size, stream_factory)
        self.REQUEST = self.create_request(request_order)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PHPWSGIInterface):
            return all((    # continuations would disallow the type: ignore comment
                self.environ == other.environ,
                self.start_response == other.start_response,    # type: ignore
                self.status_code == other.status_code,
                self.headers == other.headers,
                self.header_sent == other.header_sent,
                self.header_callbacks == other.header_callbacks,
                self.cache == other.cache,
                self.shutdown_callbacks == other.shutdown_callbacks,
                self.REQUEST == other.REQUEST,
                self.GET == other.GET,
                self.POST == other.POST,
                self.FILES == other.FILES,
                self.COOKIE == other.COOKIE
            ))
        return NotImplemented

    def create_get(self) -> MultiDict[str, str]:
        """create self.GET from self.environ"""
        try:
            query_string = self.environ["QUERY_STRING"]
        except KeyError:
            return MultiDict()
        else:
            return MultiDict(urllib.parse.parse_qsl(query_string, keep_blank_values=True))

    def create_post(self, max_size: Optional[int], stream_factory: Optional[StreamFactory]) -> Tuple[MultiDict[str, str], MultiDict[str, FilesType]]:
        """create self.POST ans self.FILES from self.environ"""
        if stream_factory is None:  # enable input data reading
            return MultiDict(), MultiDict()
        else:
            try:
                _, POST, FILES = parse_form_data(
                    self.environ,
                    stream_factory,     # type: ignore
                    max_content_length=max_size
                )
            except RequestEntityTooLarge:
                return MultiDict(), MultiDict()
            try:
                return POST, MultiDict(
                    map(lambda item: (item[0], FilesType(item[1])), FILES.items(multi=True))
                )
            except BaseException as err:   # dont leak files
                previous_exception = None
                for _, file_storage in FILES.items(multi=True):
                    try:
                        file_storage.close()
                        if valid_path(file_storage.stream.name):
                            os.unlink(file_storage.stream.name)
                    except Exception as e:  # dont stop when .close or .unlink fails
                        e.__context__ = previous_exception
                        previous_exception = e
                if previous_exception is not None:
                    raise previous_exception from err
                raise

    def create_cookie(self) -> MultiDict[str, str]:
        """create self.COOKIE from self.environ"""
        try:
            cookie_header = self.environ["HTTP_COOKIE"]
        except KeyError:
            return MultiDict()
        else:
            return werkzeug.http.parse_cookie(cookie_header, cls=UnquotingMultiDict)

    def create_request(self, request_order: Iterable[str]) -> MultiDict[str, str]:
        """create self.REQUEST by updating it with a specific order"""
        REQUEST = MultiDict()           # type: MultiDict[str, str]
        for request in request_order:   # update REQUEST in the order given by request_order
            if request == "GET":
                mapping = self.GET
            elif request == "POST":
                mapping = self.POST
            elif request == "COOKIE":
                mapping = self.COOKIE
            else:   # ignore unknown methods
                continue
            for key, values in mapping.lists():  # dont merge lists
                REQUEST.setlist(key, values)     # werkzeug already does a shallow copy
        return REQUEST

    def create_server(self) -> MutableMapping[str, Any]:
        """create self.SERVER from self.environ"""
        # SCRIPT_FILENAME, argv and argc are handled by CLIHandler
        request_time = time.time()
        SERVER = self.environ   # self.environ can be modified
        SERVER["PHP_SELF"] = self.environ.get("SCRIPT_NAME", "") \
            + self.environ.get("PATH_INFO", "")
        SERVER.setdefault("REQUEST_TIME", int(request_time))
        SERVER.setdefault("REQUEST_TIME_FLOAT", request_time)
        try:
            query_string = SERVER["QUERY_STRING"]
        except KeyError:
            pass
        else:
            SERVER.setdefault("argv", query_string)
        try:
            auth_header = self.environ["HTTP_AUTHORIZATION"]
        except KeyError:
            pass
        else:
            auth = werkzeug.http.parse_authorization_header(auth_header)
            if auth is not None:
                SERVER["PHP_AUTH_USER"] = auth.username
                SERVER["AUTH_TYPE"] = auth.type
                if auth.type == "basic":
                    SERVER["PHP_AUTH_PW"] = auth.password
                elif auth.type == "digest":
                    SERVER["PHP_AUTH_DIGEST"] = auth_header
        return SERVER

    def header(self, header: str, replace: bool = True, response_code: Optional[int] = None) -> None:
        """set a new header, replacing the old ones and changing the status code if requested"""
        if "\n" in header:    # header injection
            raise ValueError(f"the header '{header}' contains '\\r\\n'")
        name, _, value = header.partition(":")
        value = value.lstrip()  # remove whitespace between : and value
        if replace:
            self.headers[name] = value
        else:
            self.headers.add_header(name, value)
        if response_code is not None:  # set response code if given (higher priority than location headers)
            self.status_code = response_code
        elif name.lower() == "location" and not (self.status_code == 201 or self.status_code // 100 == 3):
            self.status_code = 302  # handle Location headers

    def header_remove(self, name: Optional[str] = None) -> None:
        """remove headers with a matching name or all headers if None"""
        if name is None:
            self.headers._headers.clear()   # type: ignore
        else:
            del self.headers[name]

    def headers_list(self) -> List[str]:
        """return the current headers as list"""
        return [": ".join(header) for header in self.headers.items()]

    def headers_sent(self) -> bool:
        """return if the headers have already been sent"""
        return self.header_sent

    def header_register_callback(self, callback: Callable[[], None], replace: bool = True) -> bool:
        """register a callback to be called with no arguments before the headers are send"""
        if replace:
            self.header_callbacks.clear()
        self.header_callbacks.appendleft(callback)
        return not self.header_sent

    def setcookie(
        self,
        name: str,
        value: str = "",
        expires: Optional[int] = None,
        path: Optional[str] = None,
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[str] = None
    ) -> bool:
        """set a cookie and url-encode name and value"""
        return self.setrawcookie(
            urllib.parse.quote(name, safe=""),
            f'"{urllib.parse.quote(value, safe="")}"',
            expires,
            path,
            domain,
            secure,
            httponly,
            samesite
        )

    def setrawcookie(
        self,
        name: str,
        value: str = "",
        expires: Optional[int] = None,
        path: Optional[str] = None,
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[str] = None
    ) -> bool:
        """set a cookie with encoding its value"""
        cookie = [f"{name}={value}"]
        if expires is not None:
            date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(expires))
            cookie.append(f"Expires={date}")
            cookie.append(f"Max-Age={int(expires - time.time())}")  # add both headers just in case
        if path is not None:
            cookie.append(f"Path={path}")
        if domain is not None:
            cookie.append(f"Domain={domain}")
        if secure:
            cookie.append("Secure")
        if httponly:
            cookie.append("HttpOnly")
        if samesite is not None:
            cookie.append(f"SameSite={samesite}")
        self.headers.add_header("Set-Cookie", "; ".join(cookie))
        return not self.header_sent

    def http_response_code(self, response_code: Optional[int] = None) -> int:
        """return the current status code and set a new one if requested"""
        old_code = self.status_code
        if response_code is not None:
            self.status_code = response_code
        return old_code     # is the current one if no response code has been provided

    def register_shutdown_function(self, callback: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        """register a callback to be called on shutdown"""
        self.shutdown_callbacks.appendleft((callback, args, kwargs))

    def end_headers(self) -> None:
        """call start_response with the current headers"""
        self.header_callbacks.execute()
        self.start_response(        # type: ignore
            f"{self.status_code} {HTTPStatus(self.status_code).phrase}",    # type: ignore
            self.headers.items()    # type: ignore
        )
        self.header_sent = True

    def close(self) -> None:
        """run shutdown callbacks and close self.FILES"""
        try:
            self.shutdown_callbacks.execute()
        except SystemExit:  # some callback called exit()
            pass
        finally:
            close_files(map(lambda item: item[1], self.FILES.items(multi=True)))


class PHPWSGIInterfaceFactory(WSGIInterfaceFactory):
    """factory for PHPWSGIInterfaces"""
    __slots__ = (
        "default_status",
        "default_headers",
        "cache",
        "request_order",
        "post_max_size",
        "stream_factory"
    )

    default_status: int

    default_headers: List[Tuple[str, str]]

    cache: CacheSourceContainer     # may be used by multiple factories, do not close

    request_order: Iterable[str]

    post_max_size: Optional[int]

    stream_factory: Optional[StreamFactory]

    def __init__(
        self,
        default_status: int,
        default_headers: List[Tuple[str, str]],
        cache: CacheSourceContainer,
        request_order: Iterable[str],
        post_max_size: Optional[int],
        stream_factory: Optional[StreamFactory]
    ):
        self.default_status = default_status
        self.default_headers = default_headers
        self.cache = cache
        self.request_order = request_order
        self.post_max_size = post_max_size
        self.stream_factory = stream_factory

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PHPWSGIInterfaceFactory):
            return self.default_status == other.default_status \
                and self.default_headers == other.default_headers \
                and self.cache == other.cache \
                and self.request_order == other.request_order \
                and self.post_max_size == other.post_max_size \
                and self.stream_factory == other.stream_factory
        return NotImplemented

    @staticmethod
    def parse_post_config(config: Mapping[str, Any]) -> Tuple[Optional[int], Optional[StreamFactory]]:
        """parse the post section of the config file"""
        try:
            max_size = config["max_size"]
        except KeyError:
            max_size = None
        else:
            if not isinstance(max_size, int):
                raise ValueError("value of key 'max_size' expected to be a int")
        if config.get("enable", True):
            upload_config = config.get("uploads", {})
            if upload_config.get("enable", True):
                try:
                    dir = upload_config["directory"]
                except KeyError:
                    dir = gettempdir()
                else:
                    if not isinstance(dir, str):
                        raise ValueError("value of key 'dir' expected to be a str")
                try:
                    max_files = upload_config["max_files"]
                except KeyError:
                    max_files = None
                else:
                    if not isinstance(max_files, int):
                        raise ValueError("value of key 'max_files' expected to be a int")
                return max_size, UploadStreamFactory(dir, max_files)
            else:
                return max_size, NullStreamFactory()
        else:
            return max_size, None

    @classmethod
    def from_config(cls, config: Mapping[str, Any], cache: CacheSourceContainer) -> PHPWSGIInterfaceFactory:
        """create an instance from config data"""
        try:
            status = config["default_status"]
        except KeyError:
            status = 200
        else:
            if not isinstance(status, int):
                raise ValueError("value of key 'default_status' expected to be a int")
        try:
            header_table = config["default_headers"]
        except KeyError:
            headers = [("Content-Type", 'text/html; charset="UTF-8"')]
        else:
            if isinstance(header_table, Mapping):
                headers = []
                for key, values in header_table.items():
                    if isinstance(values, Sequence):
                        for value in values:
                            if isinstance(value, str):
                                headers.append((key, value))
                            else:
                                raise ValueError(
                                    f"value of key {key} expected to be a Sequence of strings"
                                )
                    else:
                        raise ValueError(f"value of key {key} expected to be a Sequence")
            else:
                raise ValueError("value of key 'default_headers' expected to be a Mapping")
        try:
            request_order = config["request_order"]
        except KeyError:
            request_order = ("GET", "POST", "COOKIE")
        else:
            if not isinstance(request_order, Sequence):
                raise ValueError("value of key 'request_order' expected to be a Sequence")
        post_max_size, stream_factory = cls.parse_post_config(config.get("post", {}))
        return cls(
            status,
            headers,
            cache,
            request_order,
            post_max_size,
            stream_factory
        )

    def interface(self, environ: Environ, start_response: StartResponse) -> PHPWSGIInterface:
        """create an PHPWSGIInterface"""
        return PHPWSGIInterface(
            environ,
            start_response,
            self.default_status,
            Headers(self.default_headers.copy()),  # prevent changes from affecting default_headers
            self.cache,
            self.request_order,
            self.post_max_size,
            self.stream_factory
        )
