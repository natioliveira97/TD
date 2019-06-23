## @file trabalho1.py
## @title Servidor Proxy
## @author Natalia Oliveira Borges 160015863
## @author Livia Gomes Costa Fonseca 160034078


import socket
import thread
import string
import time
import os
import os.path
import re


MAX_CONNECTIONS = 30  		# Maximo de conexoes simultaneas
MAX_DATA = 4000  			# Tamanho maximo de leitura
PROXY_PORT = 8002			# Porta padrao de conexao com o browser
#TIME = 31536000				
#MAX_TIME_CACHE = 10*TIME 	# Maximo de tempo que um arquivo pode ficar na cache

## @brief Analisa a mensagem de requisicao e retorna o servidor web
## @param request Requisicao HTTP
## @return Nome do servido web
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

## @brief Analisa a mensagem de requisicao e retorna a URL desejada
## @param request Requisicao HTTP
## @return URL
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

	#print(message)

	for i in range(len(data)):
		pos = message.find(data[i])
		if(pos!=-1):

			return data[i]

	return ""

def log (url, port, state):
	print "REQUEST: ", url, "\n", "PORT: ", port, "\n", state, "\n\n"

def sendBlacklistMessage(conn):
	file = open("blacklist_message.txt", "r") 
	response = file.read()
	conn.send(response)

def sendDenyTermsMessage(conn):
	file = open("denyterms_message.txt", "r") 
	response = file.read()
	conn.send(response)

## @brief Salva o centeudo em um arquivo na cache
## @param url Url da pagina requisitada
## @param content Conteudo que sera armazenado
def saveCache(url, content):
	filename = url.replace('/', '_')
	filename = 'cache/' + filename
	cached_file = open(filename, 'a+')
	cached_file.write(content)
	cached_file.close()

## @brief Recebe o conteudo da pagina do servidor e manda para o browser
## @param request Requisicao HTTP
## @param conn Conexao HTTP
## @param webserver Servidor web
## @param port Porta usada na conexao
## @param url URL requisitada
def fileFromServer(request, conn, webserver, port, url):
	s_proxy_webserver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s_proxy_webserver.connect((webserver, port))
	s_proxy_webserver.send(request)         

	
	while 1:
		data = s_proxy_webserver.recv(MAX_DATA)
		
		if (len(data) > 0):
			conn.send(data)
			saveCache(url, data)
		else:
			break
	s_proxy_webserver.close()
	conn.close()
	log(url, port, "LOG: Conteudo do servidor")


## @brief Retorna o valor do campo ETag do cabecalho HTTP
## @param filename Nome do arquivo da cache que contem a mensagem HTTP
def getETag(filename):
	file = open(filename)

	for line in file:
		m = re.search(r'ETag:', line)
		if m:
			for part in line.split(' '):
				n = re.search(r'"', part)
				if n:
					file.close()
					return part
	file.close()
	return '0'
		


## @brief Acessa o cabecalho da pagina HTTP e verifica se o conteudo foi modificado desde o preenchimento da cache
## @param request Requisicao HTTP
## @param conn Conexao HTTP
## @param webserver Servidor web
## @param port Porta usada na conexao
## @param url URL requisitada
## @param filename Nome do arquivo da cache
## @return 1 Houve modificacoes na pagina
## @return 0 Nao houve modificacoes na pagina


# A ideia e mandar uma mensagem com a etag e, se nao tiver modificacoes, o servidor envia uma mensagem com o codigo 304
# Mas nao ta funcionando ainda e eu to com dificuldade nessa parte
def pageModified(request, conn, webserver, port, url, filename):
	etag = getETag(filename)
	request1 = request + 'If-None-Match: ' + etag + '\n'
	print '############################################'
	print '#                REQUEST                   #'
	print '############################################'
	print request1
	s_proxy_webserver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s_proxy_webserver.connect((webserver, port))
	s_proxy_webserver.send(request1) 

	data = s_proxy_webserver.recv(MAX_DATA)
	print '############################################'
	print '#                  DATA                    #'
	print '############################################'
	print data

	return 1


## @brief Retorna o tempo em que o arquivo armazenado na cache e valido, com base no cabecalho HTTP
## @param filename Nome do arquivo da cache
def freshnessLifetime(filename):
	if(os.path.exists(filename)):
		file = open(filename)

		for line in file:
			m = re.search(r'Cache-Control:', line)
			if m:
				for part in line.split(' '):
					n = re.search(r'max-age=', part)
					if n:
						Time = part.split('=')[1]
						Time = Time[:-1]
						Time = int(Time,10)
						file.close()
						return Time


		file.close()
		file = open(filename)
		i=0
		j=0
		for line in file:
			m = re.search(r'Expires:', line)
			if m:
				i=1
				expires = line.split('s: ')[1]
				result = time.strptime(expires, "%a, %d %b %Y %H:%M:%S GMT ")
				expires = time.mktime(result)
			n = re.search(r'Date:', line)
			if n:
				j=1
				date = line.split('e: ')[1]
				result = time.strptime(date, "%a, %d %b %Y %H:%M:%S GMT ")
				date = time.mktime(result)
			if i and j:
				Time = expires - date
				file.close()
				return Time


		file.close()
		file = open(filename)
		i=0
		j=0
		for line in file:
			m = re.search(r'Last-Modified:', line)
			if m:
				i=1
				last_mod = line.split('d: ')[1]
				result = time.strptime(last_mod, "%a, %d %b %Y %H:%M:%S GMT ")
				last_mod = time.mktime(result)
			n = re.search(r'Date:', line)
			if n:
				j=1
				date = line.split('e: ')[1]
				result = time.strptime(date, "%a, %d %b %Y %H:%M:%S GMT ")
				date = time.mktime(result)
			if i and j:
				Time = date - last_mod
				Time = Time/10
				file.close()
				return Time

		
		file.close()
	else:
		return 3153600	

## @brief Envia para o browser os dados requisitados
## @param request Requisicao HTTP
## @param conn Conexao HTTP
## @param webserver Servidor web
## @param port Porta usada na conexao
## @param url URL requisitada
def getData(request, conn, webserver, port, url):
	filename = url.replace('/', '_')
	filename = 'cache/' + filename

	if(os.path.exists(filename)):
		TIME = freshnessLifetime(filename)

		# Verifica se o tempo desse arquivo da cache expirou
		if( (time.time() - os.path.getmtime(filename)) > TIME ):

			if(pageModified(request, conn, webserver, port, url, filename)):
				fileFromServer(request, conn, webserver, port, url)
				return

			else:
				# Atualiza o horario do ultimo acesso e da ultima modificacao com o horario atual
				os.utime(filename, None)

		file = open(filename)
		data = file.read()
		conn.send(data)
		conn.close()
		file.close()

		log(url, port, "LOG: Conteudo da cache")

	else:
		fileFromServer(request, conn, webserver, port, url)





def  manageRequest (conn, client_addr, contador):
	# Mensagem HTTP
	request = conn.recv(MAX_DATA)

	webserver, port = findWebserver(request)
	url = findURL(request)

	isBlack = verifyBlacklist(webserver)
	if(isBlack):
		sendBlacklistMessage(conn)
		conn.close()
		log(url, port, "LOG: Site bloqueado (Blacklist)")
		return


	isWhite = verifyWhitelist(webserver)
	if(isWhite):
		try:
			getData(request, conn, webserver, port, url)
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
							getData(request, conn, webserver, port, url)
							log(url, port, "LOG: Site permitido (Sem termos proibidos)")
						else:
							sendDenyTermsMessage(conn)
							log(url, port, "LOG: Site bloqueado (Termo proibido na resposta: %s)" % verifyDenyTerms(data))
					else:
						break
				s_proxy_webserver.close()
				conn.close()
				

			except socket.error, (value, message):
				exception = "EXCEPION: " + message
				log(url, port, exception)

		else:
			sendDenyTermsMessage(conn)
			conn.close()
			log(url, port, "LOG: Site bloqueado (Termo proibido na requisicao: %s)" % verifyDenyTerms(request))
	

	conn.close()


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
			#print("Contador %s" % contador)
			conn, client_addr = s_browser_proxy.accept()
			#manageRequest(conn, client_addr, contador)

			thread.start_new_thread(manageRequest, (conn, client_addr, contador))
			contador = contador+1
		except:
			print("problem")
			break

	s_browser_proxy.close()



main()