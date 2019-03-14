import sys,re,cgi
class pyhp(object):
	def strip_all_stn(Text): #zum entfernen von \n,\t und " " am Anfang und Ende
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
		Datei = open(sys.argv[1],"r") #Datei lesen
		Datei_inhalt = strip_all_stn(Datei.read())
		Datei.close()
	except IOError: 
		print("Datei nicht gefunden") #kommt später ins Log
	except IndexError: #kein Parameter, lesen von stdin
		Datei_inhalt = input()

	if Datei_inhalt[0:6] == "<?pyhp" and (Datei_inhalt[6] == "\n" or Datei_inhalt[6] == " "): #Code beginnt am Anfang?
		code_at_begin = True
	else:
		code_at_begin = False

pyhp = pyhp()
		
pyhp.Datei_inhalt = re.split("\<\?pyhp[\n ]",pyhp.Datei_inhalt)
pyhp.erster_Abschnitt = True
if pyhp.Datei_inhalt[0] == "": #Bug in re?
	pyhp.Datei_inhalt = pyhp.Datei_inhalt[1:]

for pyhp.Abschnitt in pyhp.Datei_inhalt:
	pyhp.Abschnitt = re.split("[\n 	]\?\>",pyhp.Abschnitt)
	if pyhp.code_at_begin and pyhp.erster_Abschnitt:
		pyhp.code_at_begin = False
		pyhp.erster_Abschnitt = False
		exec(pyhp.Abschnitt[0])
		print(pyhp.Abschnitt[1],end="")
	else:	
		if pyhp.erster_Abschnitt:
			pyhp.erster_Abschnitt = False
			print(pyhp.Abschnitt[0],end="")
		else:
			exec(pyhp.Abschnitt[0])
			print(pyhp.Abschnitt[1],end="")
		


	