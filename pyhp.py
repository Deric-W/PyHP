#!/usr/bin/python3

"""Interpreter for .pyhp Scripts (https://github.com/Deric-W/PyHP-Interpreter)"""

# MIT License
#
# Copyright (c) 2019 Eric W.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time
REQUEST_TIME = time.time()
import argparse
import configparser
import sys
import os
import marshal
import re
import cgi
import urllib.parse
import importlib
from collections import defaultdict


config = "/etc/pyhp.conf"


class pyhp:
	def __init__(self):
		parser = argparse.ArgumentParser(description="Interpreter for .pyhp Scripts (https://github.com/Deric-W/PyHP-Interpreter)")
		parser.add_argument("-c", "--caching", help="enable caching (requires file)", action="store_true")
		parser.add_argument("file", type=str, help="file to be interpreted (omit for reading from stdin)", nargs="?", default="")
		args = parser.parse_args()
		self.file_path = args.file
		if args.file != "":																		# enable caching flag if file is not stdin
			self.caching = args.caching
		else:
			self.caching = False

		self.config = configparser.ConfigParser(inline_comment_prefixes="#")
		if config not in self.config.read(config):												# failed to read file
			raise ValueError("failed to read config file")

		self.print = print																		# backup for sending headers
		self.exit = exit																		# backup for exit after shutdown_functions
		self.response_code = [200, "OK"]
		self.headers = []
		self.header_sent = False
		self.header_callback = None
		self.shutdown_functions = []

		self.response_messages = {
			100: "Continue",
			101: "Switching Protocols",
			200: "OK",
			201: "Created",
			202: "Accepted",
			203: "Non-Authoritative Information",
			204: "No Content",
			205: "Reset Content",
			206: "Partial Content",
			300: "Multiple Choices",
			301: "Moved Permanently",
			302: "Found",
			303: "See Other",
			304: "Not Modified",
			305: "Use Proxy",
			307: "Temporary Redirect",
			308: "Permanent Redirect",
			400: "Bad Request",
			401: "Unauthorized",
			402: "Payment Required",
			403: "Forbidden",
			404: "Not Found",
			405: "Method Not Allowed",
			406: "Not Acceptable",
			407: "Proxy Authentication Required",
			408: "Request Timeout",
			409: "Conflict",
			410: "Gone",
			411: "Length Required",
			412: "Precondition Failed",
			413: "Payload Too Large",
			414: "URI Too Long",
			415: "Unsupported Media Type",
			416: "Range Not Satisfiable",
			417: "Expectation Failed",
			418: "I’m a teapot",
			426: "Upgrade Required",
			500: "Internal Server Error",
			501: "Not Implemented",
			502: "Bad Gateway",
			503: "Service Unavailable",
			504: "Gateway Timeout",
			505: "HTTP Version Not Supported"
		}

		self.SERVER = {																			# incomplete (AUTH)
			"PyHP_SELF": os.getenv("SCRIPT_NAME", default=""),
			"argv": os.getenv("QUERY_STRING", default=sys.argv[2:]),
			"argc": len(sys.argv) - 2,
			"GATEWAY_INTERFACE": os.getenv("GATEWAY_INTERFACE", default=""),
			"SERVER_ADDR": os.getenv("SERVER_ADDR", default=""),
			"SERVER_NAME": os.getenv("SERVER_NAME", default=""),
			"SERVER_SOFTWARE": os.getenv("SERVER_SOFTWARE", default=""),
			"SERVER_PROTOCOL": os.getenv("SERVER_PROTOCOL", default=""),
			"REQUEST_METHOD": os.getenv("REQUEST_METHOD", default=""),
			"REQUEST_TIME": int(REQUEST_TIME),
			"REQUEST_TIME_FLOAT": REQUEST_TIME,
			"QUERY_STRING": os.getenv("QUERY_STRING", default=""),
			"DOCUMENT_ROOT": os.getenv("DOCUMENT_ROOT", default=""),
			"HTTP_ACCEPT": os.getenv("HTTP_ACCEPT", default=""),
			"HTTP_ACCEPT_CHARSET": os.getenv("HTTP_ACCEPT_CHARSET", default=""),
			"HTTP_ACCEPT_ENCODING": os.getenv("HTTP_ACCEPT_ENCODING", default=""),
			"HTTP_ACCEPT_LANGUAGE": os.getenv("HTTP_ACCEPT_LANGUAGE", default=""),
			"HTTP_CONNECTION": os.getenv("HTTP_CONNECTION", default=""),
			"HTTP_HOST": os.getenv("HTTP_HOST", default=""),
			"HTTP_REFERER": os.getenv("HTTP_REFERER", default=""),
			"HTTP_USER_AGENT": os.getenv("HTTP_USER_AGENT", default=""),
			"HTTPS": os.getenv("HTTPS", default=""),
			"REMOTE_ADDR": os.getenv("REMOTE_ADDR", default=""),
			"REMOTE_HOST": os.getenv("REMOTE_HOST", default=""),
			"REMOTE_PORT": os.getenv("REMOTE_PORT", default=""),
			"REMOTE_USER": os.getenv("REMOTE_USER", default=""),
			"REDIRECT_REMOTE_USER": os.getenv("REDIRECT_REMOTE_USER", default=""),
			"SCRIPT_FILENAME": self.file_path,
			"SERVER_ADMIN": os.getenv("SERVER_ADMIN", default=""),
			"SERVER_PORT": os.getenv("SERVER_PORT", default=""),
			"SERVER_SIGNATURE": os.getenv("SERVER_SIGNATURE", default=""),
			"PATH_TRANSLATED": os.getenv("PATH_TRANSLATED", default=self.file_path),
			"SCRIPT_NAME": os.getenv("SCRIPT_NAME", default=os.path.basename(self.file_path)),
			"REQUEST_URI": os.getenv("REQUEST_URI", default=""),
			"PyHP_AUTH_DIGEST": "",
			"PyHP_AUTH_USER": "",
			"PyHP_AUTH_PW": "",
			"AUTH_TYPE": os.getenv("AUTH_TYPE", default=""),
			"PATH_INFO": os.getenv("PATH_INFO", default=""),
			"ORIG_PATH_INFO": os.getenv("PATH_INFO", default="")
		}



		if self.config.getboolean("caching", "enable") and (self.caching or self.config.getboolean("caching", "auto_caching")):
			handler_path = self.config.get("caching", "handler_path")
			cache_path = self.config.get("caching", "cache_path")
			sys.path.insert(0, handler_path)
			handler = importlib.import_module(self.config.get("caching", "handler"))				# import handler
			handler = handler.handler(cache_path, os.path.abspath(self.file_path), self.config["caching"])
			del sys.path[0]																			# cleanup for normal import behavior
			if handler.is_available():																# check if caching is possible
				if handler.is_outdated():
					self.file_content = self.prepare_file(self.file_path)
					self.file_content, self.code_at_begin = self.split_code(self.file_content)
					self.section_count = -1
					for self.section in self.file_content:
						self.section_count += 1
						if self.section_count == 0:
							if self.code_at_begin:														# first section is code, exec
								self.file_content[self.section_count][0] = compile(self.fix_indent(self.section[0], self.section_count), "<string>", "exec")
						else:																			# all sections after the first one are like [code, html until next code or eof]
							self.file_content[self.section_count][0] = compile(self.fix_indent(self.section[0], self.section_count), "<string>", "exec")
					handler.save(self.file_content, self.code_at_begin)
					self.cached = True
				else:
					self.file_content, self.code_at_begin = handler.load()
					self.cached = True
			else:																					# behave like no caching
				self.file_content = self.prepare_file(self.file_path)
				self.file_content, self.code_at_begin = self.split_code(self.file_content)
				self.cached = False
			handler.close()																			# perform cleanup tasks
		else:																						# no caching
			self.file_content = self.prepare_file(self.file_path)
			self.file_content, self.code_at_begin = self.split_code(self.file_content)
			self.cached = False

	def prepare_file(self, file_path):																# read file and handle shebang
		if file_path != "":
			with open(file_path, "r", encoding='utf-8') as file:
				file_content = file.read().split("\n")
		else: 																						# file not given, read from stdin
			file_content = input().split("\n")

		if file_content[0][:2] == "#!":																# shebang support
			file_content = "\n".join(file_content[1:])
		else:
			file_content = "\n".join(file_content)
		return file_content

	def split_code(self, code):																		# split file_content in sections like [code, html until next code or eof] with first section containing the html from the beginning if existing
		opening_tag = self.config.get("parser", "opening_tag").encode("utf8").decode("unicode_escape")	# process escape sequences like \n and \t
		closing_tag = self.config.get("parser", "closing_tag").encode("utf8").decode("unicode_escape")
		code = re.split(opening_tag, code)
		if code[0] == "":
			code_at_begin = True
			code = code[1:]
		else:
			code_at_begin = False
		index = 0
		for section in code:
			if index == 0 and not code_at_begin:
				code[index] = [section]
			else:
				code[index] = re.split(closing_tag, section, maxsplit=1)
			index += 1
		return code, code_at_begin

	def mstrip(self, text, chars): 																	# removes all chars in chars from start and end of text
		while len(text) > 0 and text[0] in chars:
			text = text[1:]
		while len(text) > 0 and text[-1] in chars:
			text = text[:-1]
		return text

	def get_indent(self, line):																		# return string and index of indent
		index = 0
		string = ""
		for char in line:
			if char in [" ", "\t"]:
				index += 1
				string += char
			else:
				break
		return [index, string]

	def is_comment(self, line):																		# return True if line is comment (first char == #)
		comment = False
		for char in line:
			if char in [" ", "\t"]:
				pass
			elif char == "#":
				comment = True
				break
			else:
				comment = False
				break
		return comment

	def fix_indent(self, code, section):
		fixed_code = ""
		linecount = 0
		first_line = True
		for line in code.split("\n"):
			linecount += 1
			if line.replace(" ", "").replace("\t", "") != "":										# not empthy
				if not self.is_comment(line):
					if first_line:
						indent = self.get_indent(line)
						first_line = False
					if len(line) > indent[0] and line[:indent[0]] == indent[1]:						# line is big enough for indent and indent is the same as first line
						fixed_code += line[indent[0]:] + "\n"
					else:
						raise IndentationError("File: " + self.file_path + " line: " + str(linecount) + " section: " + str(section))
		return fixed_code

	def http_response_code(self, response_code=None): 												# set response code
		old_response_code = self.response_code[0]
		if response_code != None:
			self.response_code = [int(response_code), self.response_messages[response_code]]
		return old_response_code

	def headers_list(self):																			# list current header
		headers = []
		for header in self.headers:
			headers.append(str(header[0]) + ": " + str(header[1]))
		return headers

	def header(self, header, replace=True, response_code=None):										# add headers and set response code
		if response_code != None:
			self.http_response_code(response_code)													# update response code if given
		header = header.split("\n")[0]																# to prevent Header-Injection
		header = header.split(":", maxsplit=1)														# to allow cookies
		header = [header[0].strip(" "), header[1].strip(" ")]
		if replace:
			new_header = []
			for stored_header in self.headers:
				if stored_header[0].lower() != header[0].lower():
					new_header.append(stored_header) 												# same header not in list
			new_header.append(header)
			self.headers = new_header
		else:
			self.headers.append(header)

	def header_remove(self, header=""):																# remove header
		if header != "":																			# remove  specific header
			header = header.lower()																	# for case-insensitivity
			new_header = []
			for stored_header in self.headers:
				if stored_header[0].lower() != header:
					new_header.append(stored_header) 												# same headers not in list
			self.headers = new_header
		else:																						# remove all headers
			self.headers = []

	def headers_sent(self):																			# true if headers already sent
		return self.header_sent

	def sent_header(self):
		self.header_sent = True
		if self.header_callback != None:
			header_callback = self.header_callback
			self.header_callback = None																# to prevent recursion if output occurs
			header_callback()																		# execute callback if set
		self.print("Status: " + str(self.response_code[0]) + " " + self.response_code[1]) 			# print status code
		mistake = True																				# no content-type header
		for header in self.headers:
			if header[0].lower() == "content-type":													# check for content-type
				mistake = False
			self.print(str(header[0]) + ": " + str(header[1])) 										# sent header
		if mistake:
			self.print("Content-Type: " + self.config.get("request", "default_mimetype"))			# sent fallback Content-Type header
		self.print()																				# end of headers

	def header_register_callback(self, callback):
		if self.header_sent:
			return False																			# headers already send
		else:
			self.header_callback = callback
			return True

	def parse_post(self):																			# parse POST without GET
		pass

	def parse_cookie(self, cookie_string, keep_blank_values=True):
		cookie_list = []
		for cookie in cookie_string.split("; "):
			cookie = cookie.split("=", maxsplit=1)													# to allow multiple "=" in value
			if len(cookie) == 1:																	# blank cookie
				if keep_blank_values:
					cookie.append("")
				else:
					continue																		# skip cookie
			if cookie[1] == "" and not keep_blank_values:											# skip cookie
				continue
			cookie[0] = urllib.parse.unquote_plus(cookie[0])										# unquote name and value
			cookie[1] = urllib.parse.unquote_plus(cookie[1])
			cookie_list.append((cookie[0], cookie[1]))
		return cookie_list

	def setcookie(self, name, value="", expires=0, path="", domain="", secure=False, httponly=False):
		name = urllib.parse.quote_plus(name)
		value = urllib.parse.quote_plus(value)
		return self.setrawcookie(name, value, expires, path, domain, secure, httponly)

	def setrawcookie(self, name, value="", expires=0, path="", domain="", secure=False, httponly=False):
		if self.header_sent:
			return False
		else:
			if type(expires) == dict:																# options array
				path = expires.get("path", "")
				domain = expires.get("domain", "")
				secure = expires.get("secure", False)
				httponly = expires.get("httponly", False)
				samesite = expires.get("samesite", "")
				expires = expires.get("expires", 0)
			else:
				samesite = ""
			cookie = "Set-Cookie:"
			cookie += name + "=" + value
			if expires != 0:
				cookie += "; " + "Expires=" + time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + expires))
			if path != "":
				cookie += "; " + "Path=" + path
			if domain != "":
				cookie += "; " + "Domain=" + domain
			if secure:
				cookie += "; " + "Secure"
			if httponly:
				cookie += "; " + "HttpOnly"
			if samesite != "":
				cookie += "; " + "SameSite=" + samesite
			self.header(cookie, False)
			return True

	def register_shutdown_function(self, callback, *args, **kwargs):
		self.shutdown_functions.append([callback, args, kwargs])


pyhp = pyhp()


def print(*args, **kwargs):																			# wrap print to auto sent headers
	if not pyhp.header_sent:
		pyhp.sent_header()
	pyhp.print(*args, **kwargs)

def exit(*args, **kwargs):																			# wrapper to exit shutdown functions
	shutdown_functions = pyhp.shutdown_functions
	pyhp.shutdown_functions = []																	# to prevent recursion if exit is called
	for func in shutdown_functions:
		func[0](*func[1], **func[2])
	pyhp.exit(*args, **kwargs)


pyhp.section_count = -1
for pyhp.section in pyhp.file_content:
	pyhp.section_count += 1
	if pyhp.section_count == 0:
		if pyhp.code_at_begin:																		# first section is code, exec
			if pyhp.cached:
				exec(pyhp.section[0])
			else:
				exec(pyhp.fix_indent(pyhp.section[0], pyhp.section_count))
			try:
				print(pyhp.section[1], end="")
			except IndexError as err:																# missing closing tag
				raise SyntaxError("File: " + pyhp.file_path + " Section: " + str(pyhp.section_count) + " Cause: missing closing Tag") from err
		else:																						# first section is just html, print
			print(pyhp.section[0], end="")
	else:																							# all sections after the first one are like [code, html until next code or eof]
		if pyhp.cached:
			exec(pyhp.section[0])
		else:
			exec(pyhp.fix_indent(pyhp.section[0], pyhp.section_count))
		try:
			print(pyhp.section[1], end="")
		except IndexError as err:
			raise SyntaxError("File: " + pyhp.file_path + " Section: " + str(pyhp.section_count) + " Cause: missing closing Tag") from err

exit(0)
