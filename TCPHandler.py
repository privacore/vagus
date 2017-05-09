import Config
import AnnouncementHandler
import socket
import logging
import threading
import select
import struct
import time
import errno

#We could have used SocketServer for this but we want to scale to at least 50
#connections and SocketServer forces us to either use 1-request-per-connection
#or 1-thread-per-connection. So instead we use lower-level select()

logger = None
listen_socket = None
handler_thread = None
out_thread = None

class OutSocket(object):
	def __init__(self,peer_addr):
		self.peer_addr = peer_addr
		self.socket = None
		self.connected = False
		self.next_connection_time = 0
		self.out_buf = ""
	def __str__(self):
		if self.socket!=None:
			sstr="%d",socket.fileno()
		else:
			sstr="<nosock>"
		return "OutSocket(%s,%s,%s,%f,%s)"%(self.peer_addr,sstr,self.connected,self.next_connection_time,self.out_buf)

out_sockets = [] #[OutSocket]
out_sockets_lock = threading.Lock()
out_sockets_wakeup_pipe = None


def initialize():
	global logger
	logger = logging.getLogger(__name__)
	if Config.tcp.port==0:
		logger.info("TCP disabled with port=0")
		return True
	
	global listen_socket
	listen_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
	listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	listen_socket.bind(("",Config.tcp.port))
	listen_socket.listen(5)
	
	global handler_thread
	handler_thread = TCPHandlerThread()
	handler_thread.start()
	
	global out_sockets_wakeup_pipe
	out_sockets_wakeup_pipe = socket.socketpair()
	for peer_addr in Config.tcp.peer:
		out_sockets.append(OutSocket(peer_addr))
	global out_thread
	out_thread = TCPOutThread()
	out_thread.start()
	
	return True


class TCPHandlerThread(threading.Thread):
	def run(self):
		client_sockets = {} #fd->(address,inbuf)
		while True:
			
			rset = [listen_socket]+client_sockets.keys()
			(readable_fds,_,_) = select.select(rset,[],[])
			
			for rfd in readable_fds:
				if rfd == listen_socket:
					(cfd,address) = listen_socket.accept()
					logger.debug("New client from %s on fd %d", address, cfd.fileno())
					client_sockets[cfd] = (address,"")
					cfd.setblocking(0)
				else:
					try:
						bytes = rfd.recv(65536)
						if len(bytes)==0:
							logger.debug("Lost connection on fd %d",rfd.fileno())
							rfd.close()
							del client_sockets[rfd]
						else:
							client_sockets[rfd] = (client_sockets[rfd][0],client_sockets[rfd][1]+bytes)
							newbuf = self.process_buffer(client_sockets[rfd][1],client_sockets[rfd][0])
							if newbuf==None:
								logger.debug("Got junk from client on fd %d",rfd.fileno())
								rfd.close()
								del client_sockets[rfd]
							else:
								client_sockets[rfd] = (client_sockets[rfd][0],newbuf)
					except socket.error, ex:
						logger.debug("Got error while reading on fd %d: %s",rfd.fileno(),ex)
						rfd.close()
						del client_sockets[rfd]

	def process_buffer(self,buf,client_address):
		while True:
			if len(buf)<5+4+1:
				return buf
			if buf[0:5]!="vagus":
				return None #junk
			(msglen,) = struct.unpack("!i",buf[5:9])
			if len(buf)<msglen:
				return buf
			else:
				msg = buf[0:msglen]
				AnnouncementHandler.process_message(msg,client_address)
				buf = buf[msglen:]



class TCPOutThread(threading.Thread):
	def run(self):
		global out_sockets
		socket_to_out_socket = {}
		while True:
			#initiate connections
			for i in range(0,len(out_sockets)):
				os = out_sockets[i]
				if os.socket==None and os.next_connection_time<time.time():
					s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
					s.setblocking(0)
					try:
						logger.debug("Initiating connection to %s",os.peer_addr)
						if ':' in os.peer_addr:
							s.connect((os.peer_addr,Config.tcp.port))
						else:
							s.connect(("::ffff:"+os.peer_addr,Config.tcp.port))
						logger.debug("Initiated connection to %s",os.peer_addr)
					except socket.error, ex:
						if ex.errno==errno.EINPROGRESS:
							pass #fine, excepected
						else:
							raise
					os.socket = s
					os.next_connection_time = time.time() + 10
					socket_to_out_socket[s] = i
			rset=[]
			wset=[]
			try:
				out_sockets_lock.acquire()
				for os in out_sockets:
					if os.socket!=None:
						if os.connected:
							if len(os.out_buf)>0:
								wset.append(os.socket)
							else:
								pass
						else:
							wset.append(os.socket)
					else:
						pass #no socket
			finally:
				out_sockets_lock.release()
			
			rset.append(out_sockets_wakeup_pipe[0])
			(readable_fds,writeable_fds,_) = select.select(rset,wset,[],10)
			
			for wfd in writeable_fds:
				i = socket_to_out_socket[wfd]
				os = out_sockets[i]
				if os.connected:
					try:
						out_sockets_lock.acquire()
						if len(os.out_buf)>0:
							#something to send
							bytes_sent = os.socket.send(os.out_buf)
							os.out_buf = os.out_buf[bytes_sent:]
						else:
							pass #nothing to send - why was this fd marked writable?
					finally:
						out_sockets_lock.release()
				else: #not connected
					err = os.socket.getsockopt(socket.SOL_SOCKET,socket.SO_ERROR)
					if err==0:
						#connected
						os.connected = True
						logger.debug("Connected to %s",os.peer_addr)
					else: #failed to connect
						del socket_to_out_socket[os.socket]
						os.socket.close()
						os.socket = None
						logger.debug("Connection to to %s failed with err=%d",os.peer_addr,err)
			for rfd in readable_fds:
				if rfd==out_sockets_wakeup_pipe[0]:
					rfd.recv(1024)
				else:
					pass #not expected
					
		
def send_announce(datagram):
	if out_sockets_wakeup_pipe==None:
		return
	global out_sockets
	try:
		out_sockets_lock.acquire()
		for os in out_sockets:
			os.out_buf += datagram
		out_sockets_wakeup_pipe[1].send("d")
	finally:
		out_sockets_lock.release()
