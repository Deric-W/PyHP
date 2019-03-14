import sys,re,cgi
class pyhp(object):
	def strip_all_stn(Text): #removes all \n,\t and " " from start and end
		chars = ["\n"," ","\t"]
		while Text[0] in chars or Text[-1] in chars:
			if Text[0] == "\t" or Text[-1] == "\t":
				Text = Text.strip("\t")
			elif Text[0] == "\n" or Text[-1] == "\n":
				Text = Text.strip("\n")
			else:
				Text = Text.strip(" ")
		return Text

	try:
		file = open(sys.argv[1],"r") #read file
		file_content = strip_all_stn(file.read())
		file.close()
	except IOError: 
		print("file not found") #Log
	except IndexError: #file not given, read from stdin
		file_content = input()

	if file_content[0:6] == "<?pyhp" and (file_content[6] == "\n" or file_content[6] == " "): #if file starts with python code
		code_at_begin = True
	else:
		code_at_begin = False
		
	file_content = re.split("\<\?pyhp[\n ]",file_content)
	first_section = True
	if file_content[0] == "": #Bug in re?
		file_content = file_content[1:]
		
pyhp = pyhp()

for pyhp.section in pyhp.file_content:
	pyhp.section = re.split("[\n 	]\?\>",pyhp.section)
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
		


	