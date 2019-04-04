import sys,re,cgi

def header(header,replace=True):
	header = header.split(":")
	header = [header[0].strip(" "),header[1].strip(" ")]
	if replace:
		new_header = []
		for stored_header in pyhp.header:
			if stored_header[0].lower() != header[0].lower():
				new_header.append(stored_header) #same headers not in list
		new_header.append(header)
		pyhp.header = new_header
	else:
		pyhp.header.append(header)
		
def header_remove(header):
	header = header.split(":")
	header = [header[0].strip(" "),header[1].strip(" ")]
	new_header = []
	for stored_header in pyhp.header:
		if stored_header[0].lower() != header[0].lower() or stored_header[1].lower() != header[1].lower():
			new_header.append(stored_header) #same headers not in list
	pyhp.header = new_header

def headers_sent():
	return pyhp.header_sent

class pyhp(object):
	def strip_all_stn(Text): #removes all \n,\t and " " from start and end
		chars = ["\n"," ","\t"]
		while Text[0] in chars:
			Text = Text[1:]
		while Text[-1] in chars:
			Text = Text[:-1]
		return Text
	
	def send_header(self):
		mistake = True
		for header in self.header:
			if header[0].lower() == "content-type":
				mistake = False
			print(str(header[0]) + ":" + str(header[1]))
		if mistake:
			print("Content-Type:text/html")
		print()
		self.header_sent = True
	
	header = []
	header_sent = False
	
	try:
		file = open(sys.argv[1],"r") #read file
		file_content = strip_all_stn(file.read())
		file.close()
	except IndexError: #file not given, read from stdin
		file_content = input()

	if file_content[:6] == "<?pyhp" and file_content[6] in ["\n"," ","\t"]: #if file starts with python code
		code_at_begin = True
	else:
		code_at_begin = False
		
	file_content = re.split("\<\?pyhp[\n \t]",file_content)
	first_section = True
	if file_content[0] == "": #if match at begin
		file_content = file_content[1:]
		
pyhp = pyhp()

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
		


	