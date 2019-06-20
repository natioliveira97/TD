import socket
import thread
import string


MAX_CONNECTIONS = 50
MAX_DATA = 4000
PROXY_PORT = 8001

def findWebserver (request):
	# Divide a mensagem em linhas
	lines = request.split('\n')

	for i in range(len(lines)):
		words = lines[i].split(' ')
		if(words[0] == "Host:"):
			# print("Tem host")
			port = int("80")
			webserver = words[1]
			# print(len(webserver))
			if(ord(webserver[len(webserver)-1]) < 37):
				# print("remover ultimo")
				webserver = webserver[:-1]
				# print(len(webserver))
			port_pos = webserver.find(":")
			if(port_pos != -1):
				port = int(webserver[port_pos+1:])
				webserver = webserver[:port_pos]
			print(webserver,port,lines[0])
			return webserver, port

		# else:
		# 	print("Nao tem host")
	return "noServer", -1



def  manageRequest (conn, client_addr, contador):
	# Mensagem HTTP
	request = conn.recv(MAX_DATA)
	#print(request)

	webserver, port = findWebserver(request)


	try:
		# create a socket to connect to the web server
		s_proxy_webserver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s_proxy_webserver.connect((webserver, port))
		s_proxy_webserver.send(request)         # send request to webserver

		
		while 1:
			# receive data from web server
			data = s_proxy_webserver.recv(MAX_DATA)
			
			if (len(data) > 0):
				# send to browser
				conn.send(data)
			else:
				break
		s_proxy_webserver.close()
		conn.close()
		print("CLOSED %s" % contador)
	except socket.error, (value, message):
		print(message)







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
			contador = contador+1
			thread.start_new_thread(manageRequest, (conn, client_addr,contador))
		except:
			print("problem")
			break

	s_browser_proxy.close()

main()