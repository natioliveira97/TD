from socket import * 
import sys
import os , os.path
import shutil
from collections import deque
from httplib import HTTPResponse
from StringIO import StringIO

class StringToHTTPResponse():
    def __init__(self, response_str):
        self._file = StringIO(response_str)
    def makefile(self, *args, **kwargs):
        return self._file

class pycolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m' # End color
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def colorizeLog(shouldColorize, log_level, msg):
    ## Higher is the log_level in the log()
    ## argument, the lower is its priority.
    colorize_log = {
    "NORMAL": pycolors.ENDC,
    "WARNING": pycolors.WARNING,
    "SUCCESS": pycolors.OKGREEN,
    "FAIL": pycolors.FAIL,
    "RESET": pycolors.ENDC,
    "BLUE":pycolors.OKBLUE
    }

    if shouldColorize.lower() == "true":
        if log_level in colorize_log:
            return colorize_log[str(log_level)] + msg + colorize_log['RESET']
        return colorize_log["NORMAL"] + msg + colorize_log["RESET"]
    return msg

PORT = 8001
host = ""

# Create a server socket, bind it to a port and start listening 
tcpSerSock = socket(AF_INET, SOCK_STREAM)
tcpSerSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
tcpSerSock.bind((host, PORT))
tcpSerSock.listen(5) 
cached_files = deque()
cache_dict_obj = {}
cache_dict_string = {}

while 1:
    # Start receiving data from the client 
    print 'Ready to serve...' 

    tcpCliSock, addr = tcpSerSock.accept() 
    print 'Received a connection from:', addr

    message = tcpCliSock.recv(1024)
    # print message

    # Extract the filename from the given message 
    filename = message.split()[1].partition("/")[2] 
    if(filename[-1:] == '/'):
        filename = filename[:-1]

    slashIndices = [i for i, letter in enumerate(filename) if letter == '/'] 
    filetouse = filename[slashIndices[1]+1:]

    hostn = filename.replace("www.","",1).split("/")[1].split(":")[0] # Strip the hostname


    # Check wether the file exist in the cache 
    if filetouse in cache_dict_obj: # Proxy Server finds a cache hit and generates a response message
        print colorizeLog("true", "SUCCESS","FILE PRESENT IN CACHE")

        cacheObj = cache_dict_obj[filetouse]
        print cacheObj.getheaders()
        if(cacheObj.getheader('cache-control') == 'must-revalidate'):
            print colorizeLog("true", "BLUE","NEED TO REVALIDATE")
            date = cacheObj.getheader('date')
            c = socket(AF_INET, SOCK_STREAM)
            c.connect((hostn, 20000))
            fileobj = c.makefile('r', 0)
            fileobj.write("GET "+"/" + filetouse + " HTTP/1.1\n" + "If-Modified-Since: " + date + "\n\n")

            tempString = c.recv(4096)
            responseString = ""
            while tempString:
                responseString += tempString
                tempString = c.recv(4096)

            source = StringToHTTPResponse(responseString)
            responseObj = HTTPResponse(source)
            responseObj.begin()

            if(responseObj.status == 200):
                print colorizeLog("true", "SUCCESS","CHANGED FILE SENT. CACHE MODIFIED")
                cache_dict_obj[filetouse] = responseObj
                cache_dict_string[filetouse] = responseString
            else:
                print colorizeLog("true", "SUCCESS","SERVER FILE NOT CHANGED. FILE DIRECTLY SENT FROM PROXY CACHE.")

            c.close()

        else:
            print colorizeLog("true", "SUCCESS","NO REVALIDATION. FILE DIRECTLY RETURNED FROM CACHE.")

        tcpCliSock.send(cache_dict_string[filetouse])
        cached_files.remove(filetouse)
        cached_files.append(filetouse)

    else: 
        c = socket(AF_INET, SOCK_STREAM) # Create a socket on the proxyserver

        try: 
            # Connect to the socket to port 20000
            c.connect((hostn, 20000)) 
            # Create a temporary file on this socket and ask port 20000 for the file requested by the client
            fileobj = c.makefile('r', 0)
            fileobj.write("GET "+"/" + filetouse + "  HTTP/1.1\n\n")   

            # Read the response into buffer 
            tempString = c.recv(4096)
            responseString = ""
            while tempString:
                responseString += tempString
                tempString = c.recv(4096)

            # Make response object from response string
            source = StringToHTTPResponse(responseString)
            responseObj = HTTPResponse(source)
            responseObj.begin()

            if responseObj.status == 200:
                # Create a new file in the cache for the requested file.  
                if(len(cached_files) < 3):
                    cached_files.append(filetouse)
                    cache_dict_obj[filetouse] = responseObj
                    cache_dict_string[filetouse] = responseString
                else:
                    popped_file = cached_files.popleft()
                    del cache_dict_obj[popped_file]
                    del cache_dict_string[popped_file]
                    cached_files.append(filetouse)
                    cache_dict_obj[filetouse] = responseObj
                    cache_dict_string[filetouse] = responseString
                print colorizeLog("true", "SUCCESS", "200: OK")
            else:
                printString = "Status code " + str(responseObj.status) + ": " + responseObj.reason
                print colorizeLog("true", "WARNING", printString)
            # Send the responseString in the buffer to client socket and the corresponding file in the cache  
            tcpCliSock.send(responseString)

        except Exception,e:
            print str(e) 
            print colorizeLog("true", "FAIL","Illegal request")

        c.close()

    tcpCliSock.close()