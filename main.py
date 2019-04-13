import sys
import re
import cgi

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
		self.response_code = [200,"OK"]
		self.headers = []
		self.header_sent = False

		data = cgi.FieldStorage()
		self.REQUEST = {}
		for key in data:					#build $_REQUEST array from PHP
			self.REQUEST[key] = data.getvalue(key)

		try:
			file = open(sys.argv[1],"r") #read file
			self.file_content = self.strip_all_stn(file.read())
			file.close()
		except IndexError: #file not given, read from stdin
			self.file_content = input()

		if self.file_content[:6] == "<?pyhp" and self.file_content[6] in ["\n"," ","\t"]: #if file starts with python code
			self.code_at_begin = True
		else:
			self.code_at_begin = False
		
		self.file_content = re.split("\<\?pyhp[\n \t]",self.file_content)
		self.first_section = True
		if self.file_content[0] == "": #if match at begin
			self.file_content = self.file_content[1:]	

	def strip_all_stn(self,Text): #removes all \n,\t and " " from start and end of text
		chars = ["\n"," ","\t"]
		while Text[0] in chars:
			Text = Text[1:]
		while Text[-1] in chars:
			Text = Text[:-1]
		return Text
	
	def http_response_code(self,response_code=None): #set response code
		old_response_code = self.response_code
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