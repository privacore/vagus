import SocketServer
import threading

class CommandRequestHandler(SocketServer.StreamRequestHandler):
	def handle(self):
		while True:
			data = self.rfile.readline()
			if len(data)==0: #socket closed?
				break
			command_line = data.rstrip("\r\n")
			response = self.server.command_callback(command_line)
			if response==None:
				break
			self.wfile.write(response)



class AddrReuseTCPServer(SocketServer.TCPServer):
	def __init__(self, server_address, RequestHandlerClass):
		self.allow_reuse_address = True
		SocketServer.TCPServer.__init__(self,server_address,RequestHandlerClass)


class TCPCommandLineServer(AddrReuseTCPServer):
	def __init__(self, port, command_callback):
		AddrReuseTCPServer.__init__(self,("",port), CommandRequestHandler)
		self.command_callback = command_callback
	

	
if __name__ == "__main__":
	import socket, time
	class ServeThread(threading.Thread):
		def __init__(self,tcp_server):
			threading.Thread.__init__(self)
			self.tcp_server = tcp_server
		def run(self):
			self.tcp_server.serve_forever()
	
	last_command=None
	def test_callback(command_line):
		global last_command
		last_command = command_line
		print "test_callback: command_line=",command_line
		return "ok:"+command_line
	
	server = TCPCommandLineServer(12345,test_callback)
	thread = ServeThread(server)
	thread.start()
	
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	s.connect(("localhost",12345))
	
	s.send("hello\n")
	time.sleep(0.5)
	assert last_command=="hello"
	s.setblocking(0)
	assert s.recv(1024) == "ok:hello"
	
	s.send("hello2\n")
	time.sleep(0.5)
	assert last_command=="hello2"
	s.setblocking(0)
	assert s.recv(1024) == "ok:hello2"
	
	s.close()
	
	server.shutdown()
