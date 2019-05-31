#!/usr/bin/python3
import time
REQUEST_TIME = time.time()
import sys
import os
import marshal
import re
import cgi
import urllib.parse
from collections import defaultdict


class pyhp:
	def __init__(self):
		if len(sys.argv) > 1:																	# file or parameter exist
			if sys.argv[1] == "-c":																# chache enabled
				self.caching = True
				try:
					self.file_path = sys.argv[2]
				except IndexError:
					self.file_path = ""
					self.caching = False														# cache only for files
			else:
				self.caching = False
				self.file_path = sys.argv[1]
		else:
			self.caching = False
			self.file_path = ""

		self.response_messages = {																# incomplete
			"200": "OK",
			"300": "Multiple Choices",
			"301": "Moved Permanently",
			"307": "Temporary Redirect",
			"308": "Permanent Redirect",
			"400": "Bad Request",
			"404": "Not Found",
			"418": "I’m a teapot",
			"500": "Internal Server Error"
		}

		self.SERVER = {																			# incomplete too (AUTH)
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
			"AUTH_TYPE": "",
			"PATH_INFO": os.getenv("PATH_INFO", default=""),
			"ORIG_PATH_INFO": os.getenv("PATH_INFO", default="")
		}

		self.print = print																			# backup for sending headers
		self.response_code = [200, "OK"]
		self.headers = []
		self.header_sent = False
		self.first_section = True
		self.section_count = -1

		data = cgi.FieldStorage()																	# build $_REQUEST array from PHP
		self.REQUEST = defaultdict(lambda: "")
		for key in data:
			self.REQUEST[key] = data.getvalue(key)													# to contain lists instead of multiple FieldStorages if key has multiple values

		data = urllib.parse.parse_qsl(self.SERVER["QUERY_STRING"], keep_blank_values=True)
		self.GET = defaultdict(lambda: "")
		for pair in data:																			# build $_GET
			if not pair[0] in self.REQUEST:															# if value is blank
				self.REQUEST[pair[0]] = pair[1]
			self.GET[pair[0]] = self.REQUEST[pair[0]]												# copy value from REQUEST

		self.POST = defaultdict(lambda: "")
		for key in self.REQUEST:																	# build $_POST
			if key not in self.GET:																	# REQUEST - GET = POST
				self.POST[key] = self.REQUEST[key]

		data = os.getenv("HTTP_COOKIE", default="")
		self.COOKIE = defaultdict(lambda: "")
		if data != "":																				# to avoid non existent blank cookies
			for cookie in data.split(";"):															# build $_COOKIE
				cookie = cookie.split("=")
				if len(cookie) > 2:																	# multiple = in cookie
					cookie[1] = "=".join(cookie[1:])
				if len(cookie) == 1:																# blank cookie
					cookie.append("")
				cookie[0] = cookie[0].strip(" ")
				try:																				# to handle blank values
					if cookie[1][0] == " ":															# remove only potential space after =
						cookie[1] = cookie[1][1:]
				except IndexError:
					pass
				cookie[0] = urllib.parse.unquote_plus(cookie[0])
				cookie[1] = urllib.parse.unquote_plus(cookie[1])
				if cookie[0] in self.COOKIE:
					if type(self.COOKIE[cookie[0]]) == str:
						self.COOKIE[cookie[0]] = [self.COOKIE[cookie[0]], cookie[1]]				# make new list
					else:
						self.COOKIE[cookie[0]].append(cookie[1])									# append to existing list
				else:
					self.COOKIE[cookie[0]] = cookie[1]												# make new string

		for cookie in self.COOKIE:																	# merge COOKIE with REQUEST, prefer COOKIE
			self.REQUEST[cookie] = self.COOKIE[cookie]

		if self.caching and self.SERVER["PyHP_SELF"] != "":
			cache_path = "/etc/pyhp/" + self.SERVER["PyHP_SELF"] + ".cache"
			if not os.path.isfile(cache_path) or os.path.getmtime(cache_path) < os.path.getmtime(self.file_path):		# renew cache if outdated or not exist
				if not os.path.isdir(os.path.dirname(cache_path)):									# auto create directories
					os.makedirs(os.path.dirname(cache_path), exist_ok=True)
				self.file_content = self.prepare_file(self.file_path)
				with open(cache_path, "wb") as cache:
					self.file_content = self.split_code(self.file_content)
					code_at_begin = self.code_at_begin												# to restore it later
					for self.section in self.file_content:											# compile python parts without print html parts
						self.section_count += 1
						if self.code_at_begin and self.first_section:
							self.code_at_begin = False
							self.first_section = False
							self.file_content[self.section_count][0] = compile(self.fix_indent(self.section[0], self.section_count), "<string>", "exec")
						else:
							if self.first_section:
								self.first_section = False
							else:
								self.file_content[self.section_count][0] = compile(self.fix_indent(self.section[0], self.section_count), "<string>", "exec")
					self.code_at_begin = code_at_begin												# restore old data
					self.first_section = True
					self.section_count = -1
					marshal.dump({"code_at_begin": code_at_begin, "code": self.file_content}, cache)
					self.cached = True
			else:																					# load cache
				with open(cache_path, "rb") as cache:
					self.file_content = marshal.load(cache)
					self.code_at_begin = self.file_content["code_at_begin"]
					self.file_content = self.file_content["code"]
					self.cached = True
		else:																						# no caching
			self.file_content = self.prepare_file(self.file_path)
			self.file_content = self.split_code(self.file_content)
			self.cached = False

	def prepare_file(self, file_path):																# read file and handle shebang
		if file_path != "":
			file = open(file_path, "r", encoding='utf-8') 											# read file
			file_content = file.read().split("\n")
			file.close()
		else: 																						# file not given, read from stdin
			file_content = input().split("\n")

		if file_content[0][:2] == "#!":																# shebang support
			file_content = "\n".join(file_content[1:])
		else:
			file_content = "\n".join(file_content)
		return file_content

	def split_code(self, code):
		code = re.split("\<\?pyhp[\n \t]", code)
		if code[0] == "":
			self.code_at_begin = True
			code = code[1:]
		else:
			self.code_at_begin = False
		index = 0
		for section in code:
			code[index] = re.split("[\n \t]\?\>", section, maxsplit=1)
			index += 1
		return code

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
			if line.replace(" ","").replace("\t", "") != "":										# not empthy
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
			self.response_code = [int(response_code), self.response_messages[str(response_code)]]
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

	def header_remove(self, header):																# remove header
		header = header.split(":")
		header = [header[0].strip(" "), header[1].strip(" ")]
		new_header = []
		for stored_header in self.headers:
			if stored_header[0].lower() != header[0].lower() or stored_header[1].lower() != header[1].lower():
				new_header.append(stored_header) 													# same headers not in list
		self.headers = new_header

	def headers_sent(self):																			# true if headers already sent
		return self.header_sent

	def sent_header(self):
		self.print("Status: " + str(self.response_code[0]) + " " + self.response_code[1]) 			# print status code
		mistake = True																				# no content-type header
		for header in self.headers:
			if header[0].lower() == "content-type":													# check for content-type
				mistake = False
			self.print(str(header[0]) + ": " + str(header[1])) 										# sent header
		if mistake:
			self.print("Content-Type: text/html")													# sent fallback Content-Type header
		self.print()																				# end of headers
		self.header_sent = True

	def setcookie(self, name, value="", expires=0, path="", domain="", secure=False, httponly=False):
		name = urllib.parse.quote_plus(name)
		value = urllib.parse.quote_plus(value)
		return self.setrawcookie(name, value, expires, path, domain, secure, httponly)

	def setrawcookie(self, name, value="", expires=0, path="", domain="", secure=False, httponly=False):
		if self.header_sent:
			return False
		else:
			if type(value) == dict:																	# options array
				expires = value["expires"]
				path = value["path"]
				domain = value["domain"]
				secure = value[" secure"]
				httponly = value["httponly"]
				samesite = value["samesite"]
			else:
				samesite = ""
			cookie = "Set-Cookie:"
			cookie += name + "=" + value
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
				cookie += "; " + samesite
			self.header(cookie, False)
			return True


pyhp = pyhp()

def print(*args, **kwargs):																			# wrap print to auto sent headers
	if not pyhp.header_sent:
		pyhp.sent_header()
	pyhp.print(*args, **kwargs)

for pyhp.section in pyhp.file_content:
	pyhp.section_count += 1
	if pyhp.code_at_begin and pyhp.first_section:
		pyhp.code_at_begin = False
		pyhp.first_section = False
		if pyhp.cached:
			exec(pyhp.section[0])
		else:
			exec(pyhp.fix_indent(pyhp.section[0], pyhp.section_count))
		try:
			print(pyhp.section[1], end="")
		except IndexError as err:
			raise SyntaxError("File: " + pyhp.file_path + "Section: " + str(pyhp.section_count)) from err
	else:
		if pyhp.first_section:
			pyhp.first_section = False
			print(pyhp.section[0], end="")
		else:
			if pyhp.cached:
				exec(pyhp.section[0])
			else:
				exec(pyhp.fix_indent(pyhp.section[0], pyhp.section_count))
			try:
				print(pyhp.section[1], end="")
			except IndexError as err:
				raise SyntaxError("File: " + pyhp.file_path + "Section: " + str(pyhp.section_count)) from err
