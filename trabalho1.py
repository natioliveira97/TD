import socket
import thread
import string


MAX_CONNECTIONS = 50
MAX_DATA = 4000
PROXY_PORT = 8002

def findWebserver (request):
	# Divide a mensagem em linhas
	lines = request.split('\n')

	# Encontra cabecalho host
	for i in range(len(lines)):

		words = lines[i].split(' ')

		if(words[0] == "Host:"):
			port = int("80")
			webserver = words[1]

			# Retira ultimo character
			if(ord(webserver[len(webserver)-1]) < 37):
				webserver = webserver[:-1]

			# Verifica se a mensagem estabelece conexao em outra porta
			port_pos = webserver.find(":")
			if(port_pos != -1):
				port = int(webserver[port_pos+1:])
				webserver = webserver[:port_pos]

			return webserver, port

	return "noServer", -1

def findURL (request):
	# Encontra url
	lines = request.split('\n')
	words = lines[0].split(' ')
	url = words[1]

	return url

def verifyWhitelist (webserver):

	whitelist = open("whitelist.txt", "r") 
	data = whitelist.read()
	data = data.split('\n')

	for i in range(len(data)):
		if(webserver == data[i]):
			return True

	return False

def verifyBlacklist (webserver):

	blacklist = open("blacklist.txt", "r") 
	data = blacklist.read()
	data = data.split('\n')

	for i in range(len(data)):
		if(webserver == data[i]):
			return True

	return False

def verifyDenyTerms (message):
	deny_terms = open("deny_terms.txt", "r") 
	data = deny_terms.read()
	data = data.split('\n')

	for i in range(len(data)):
		if(message.find(data[i])!=-1):
			return data[i]

	return ""

def log (url, port, state):
	print "REQUEST: ", url, "\n", "PORT: ", port, "\n", state, "\n\n"

def sendBlacklistMessage(conn):
	file = open("blacklist_message.txt", "r") 
	response = file.read()
	conn.send(response)

def  manageRequest (conn, client_addr, contador):
	# Mensagem HTTP
	request = conn.recv(MAX_DATA)

	webserver, port = findWebserver(request)
	url = findURL(request)

	print(webserver, port)

	isBlack = verifyBlacklist(webserver)
	if(isBlack):
		sendBlacklistMessage(conn)
		conn.close()
		log(url, port, "LOG: Site bloqueado (Blacklist)")
		return


	isWhite = verifyWhitelist(webserver)
	if(isWhite):
		try:
			s_proxy_webserver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s_proxy_webserver.connect((webserver, port))
			s_proxy_webserver.send(request)         

			
			while 1:
				data = s_proxy_webserver.recv(MAX_DATA)
				
				if (len(data) > 0):
					conn.send(data)
				else:
					break
			s_proxy_webserver.close()
			conn.close()
			log(url, port, "LOG: Site permitido (Whitelist)")

		except socket.error, (value, message):
			exception = "EXCEPION: " + message
			log(url, port, exception)

	else:
		if(verifyDenyTerms(request) == ""):

			try:
				s_proxy_webserver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s_proxy_webserver.connect((webserver, port))
				s_proxy_webserver.send(request)         
			
				while 1:
					data = s_proxy_webserver.recv(MAX_DATA)
					
					if (len(data) > 0):
						if(verifyDenyTerms(data) == ""):
							conn.send(data)
							log(url, port, "LOG: Site permitido (Sem termos proibidos)")
						else:
							sendBlacklistMessage(conn)
							log(url, port, "LOG: Site bloqueado (Termo proibido na resposta: %s)" % verifyDenyTerms(data))
					else:
						break
				s_proxy_webserver.close()
				conn.close()
				

			except socket.error, (value, message):
				exception = "EXCEPION: " + message
				log(url, port, exception)

		else:
			sendBlacklistMessage(conn)
			conn.close()
			log(url, port, "LOG: Site bloqueado (Termo proibido na requisicao: %s)" % verifyDenyTerms(request))
	



	conn.close()
	print("CLOSED %s" % contador)








def main():

	# O browser de internet deve ser configurado para operar na porta definida.
	port = PROXY_PORT
	host = ""
	contador = 0

	# Criando uma conexao socket entre o browser e o servido proxy
	s_browser_proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s_browser_proxy.bind((host,port))
	s_browser_proxy.listen(MAX_CONNECTIONS)

	# Ficar ouvindo a porta e interceptando pacotes
	while 1:
		try:
			print("Contador %s" % contador)
			conn, client_addr = s_browser_proxy.accept()
			#manageRequest(conn, client_addr, contador)

			thread.start_new_thread(manageRequest, (conn, client_addr, contador))
			contador = contador+1
		except:
			print("problem")
			break

	s_browser_proxy.close()



main()