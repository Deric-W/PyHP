#!/usr/bin/python3
import time
REQUEST_TIME = time.time()
import sys
import os
import re
import cgi
from collections import defaultdict

class pyhp:
	def __init__(self):
		self.print = print		#backup for sending headers
		self.response_messages = {
			"200":"OK",
			"300":"Multiple Choices",
			"301":"Moved Permanently",
			"307":"Temporary Redirect",
			"308":"Permanent Redirect",
			"400":"Bad Request",
			"404":"Not Found",
			"418":"I’m a teapot",
			"500":"Internal Server Error"
		}									#incomplete
		try:								#to prevent IndexError
			sys.argv[1]
		except:
			sys.argv.append("")
		self.SERVER = {
			"PyHP_SELF":os.getenv("SCRIPT_NAME",default=""),
			"argv": os.getenv("QUERY_STRING",default=sys.argv[2:]),
			"argc":len(sys.argv) - 2,
			"GATEWAY_INTERFACE": os.getenv("GATEWAY_INTERFACE",default=""),
			"SERVER_ADDR": os.getenv("SERVER_ADDR",default=""),
			"SERVER_NAME": os.getenv("SERVER_NAME",default=""),
			"SERVER_SOFTWARE": os.getenv("SERVER_SOFTWARE",default=""),
			"SERVER_PROTOCOL": os.getenv("SERVER_PROTOCOL",default=""),
			"REQUEST_METHOD": os.getenv("REQUEST_METHOD",default=""),
			"REQUEST_TIME": int(REQUEST_TIME),
			"REQUEST_TIME_FLOAT": REQUEST_TIME,
			"QUERY_STRING": os.getenv("QUERY_STRING",default=""),
			"DOCUMENT_ROOT": os.getenv("DOCUMENT_ROOT",default=""),
			"HTTP_ACCEPT": os.getenv("HTTP_ACCEPT",default=""),
			"HTTP_ACCEPT_CHARSET": os.getenv("HTTP_ACCEPT_CHARSET",default=""),
			"HTTP_ACCEPT_ENCODING": os.getenv("HTTP_ACCEPT_ENCODING",default=""),
			"HTTP_ACCEPT_LANGUAGE": os.getenv("HTTP_ACCEPT_LANGUAGE",default=""),
			"HTTP_CONNECTION": os.getenv("HTTP_CONNECTION",default=""),
			"HTTP_HOST": os.getenv("HTTP_HOST",default=""),
			"HTTP_REFERER": os.getenv("HTTP_REFERER",default=""),
			"HTTP_USER_AGENT": os.getenv("HTTP_USER_AGENT",default=""),
			"HTTPS": os.getenv("HTTPS",default=""),
			"REMOTE_ADDR": os.getenv("REMOTE_ADDR",default=""),
			"REMOTE_HOST": os.getenv("REMOTE_HOST",default=""),
			"REMOTE_PORT": os.getenv("REMOTE_PORT",default=""),
			"REMOTE_USER": os.getenv("REMOTE_USER",default=""),
			"REDIRECT_REMOTE_USER": os.getenv("REDIRECT_REMOTE_USER",default=""),
			"SCRIPT_FILENAME": sys.argv[1],
			"SERVER_ADMIN": os.getenv("SERVER_ADMIN",default=""),
			"SERVER_PORT": os.getenv("SERVER_PORT",default=""),
			"SERVER_SIGNATURE": os.getenv("SERVER_SIGNATURE",default=""),
			"PATH_TRANSLATED": os.getenv("PATH_TRANSLATED",default=sys.argv[1]),
			"SCRIPT_NAME": os.getenv("SCRIPT_NAME",default=os.path.basename(sys.argv[1])),
			"REQUEST_URI": os.getenv("REQUEST_URI",default=""),
			"PyHP_AUTH_DIGEST":"",
			"PyHP_AUTH_USER":"",
			"PyHP_AUTH_PW":"",
			"AUTH_TYPE":"",
			"PATH_INFO": os.getenv("PATH_INFO",default=""),
			"ORIG_PATH_INFO": os.getenv("PATH_INFO",default="")
		}										#incomplete too (AUTH)

		self.response_code = [200,"OK"]
		self.headers = []
		self.header_sent = False

		data = cgi.FieldStorage()
		self.REQUEST = defaultdict(lambda: "")
		for key in data:					#build $_REQUEST array from PHP
			self.REQUEST[key] = data.getvalue(key)

		if sys.argv[1] != "":
			file = open(sys.argv[1],"r",encoding='utf-8') #read file
			self.file_content = file.read().split("\n")
			file.close()
		else: #file not given, read from stdin
			self.file_content = input().split("\n")

		if self.file_content[0][:2] == "#!":				#shebang
			self.file_content = self.mstrip("\n".join(self.file_content[1:]),["\n"," ","\t"])
		else:
			self.file_content = self.mstrip("\n".join(self.file_content),["\n"," ","\t"])

		if self.file_content[:6] == "<?pyhp" and self.file_content[6] in ["\n"," ","\t"]: #if file starts with python code
			self.code_at_begin = True
		else:
			self.code_at_begin = False
		
		self.file_content = re.split("\<\?pyhp[\n \t]",self.file_content)
		self.first_section = True
		if self.file_content[0] == "": #if match at begin
			self.file_content = self.file_content[1:]	

	def mstrip(self,text,chars): #removes all chars in chars from start and end of text
		while len(text) > 0 and text[0] in chars:
			text = text[1:]
		while len(text) > 0 and text[-1] in chars:
			text = text[:-1]
		return text

	def get_indent(self,line):						#return string and index of indent
		index = 0
		string = ""
		for char in line:
			if char in [" ","\t"]:
				index = index + 1
				string = string + char
			else:
				break
		return [index,string]

	def is_comment(self,line):						# return True if line is comment
		comment = False
		for char in line:
			if char in [" ","\t"]:
				pass
			elif char == "#":
				comment = True
				break
			else:
				comment = False
				break
		return comment

	def fix_indent(self,code):
		pass 										#todo
	
	def http_response_code(self,response_code=None): #set response code
		old_response_code = self.response_code[0]
		if response_code != None:
			self.response_code = [int(response_code),self.response_messages[str(response_code)]]
		return old_response_code
	
	def headers_list(self):		#list current header
		headers = []
		for header in self.headers:
			headers.append(str(header[0]) + ": " + str(header[1]))
		return headers
	
	def header(self,header,replace=True,response_code=None):	#add headers and set response code
		if response_code != None:
			self.http_response_code(response_code)				#update response code if given
		header = header.split("\n")[0]							#to prevent Header-Injection
		header = header.split(":")
		header = [header[0].strip(" "),header[1].strip(" ")]
		if replace:
			new_header = []
			for stored_header in self.headers:
				if stored_header[0].lower() != header[0].lower():
					new_header.append(stored_header) #same headers not in list
			new_header.append(header)
			self.headers = new_header
		else:
			self.headers.append(header)
	
	def header_remove(self,header):	#remove header
		header = header.split(":")
		header = [header[0].strip(" "),header[1].strip(" ")]
		new_header = []
		for stored_header in self.headers:
			if stored_header[0].lower() != header[0].lower() or stored_header[1].lower() != header[1].lower():
				new_header.append(stored_header) #same headers not in list
		self.headers = new_header
	
	def headers_sent(self):		#true if headers already sent
		return self.header_sent
	
	def sent_header(self):
		self.print("Status: " + str(self.response_code[0]) + " " + self.response_code[1]) #print status code
		mistake = True		#no content-type header
		for header in self.headers:
			if header[0].lower() == "content-type":	#check for content-type
				mistake = False
			self.print(str(header[0]) + ": " + str(header[1])) #sent header
		if mistake:
			self.print("Content-Type: text/html")
		self.print()		#end of headers
		self.header_sent = True
	
pyhp = pyhp()

def print(*args,**kwargs):					#wrap print to auto sent headers
	if not pyhp.header_sent:
		pyhp.sent_header()
	pyhp.print(*args,**kwargs)

for pyhp.section in pyhp.file_content:
	pyhp.section = re.split("[\n \t]\?\>",pyhp.section)
	if pyhp.code_at_begin and pyhp.first_section:
		pyhp.code_at_begin = False
		pyhp.first_section = False
		exec(pyhp.section[0])
		print(pyhp.section[1],end="")
	else:	
		if pyhp.first_section:
			pyhp.first_section = False
			print(pyhp.section[0],end="")
		else:
			exec(pyhp.section[0])
			print(pyhp.section[1],end="")	