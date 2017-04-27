from TCPCommandLineServer import TCPCommandLineServer
import Config
import InstanceRegistry
import VagusRegistry
import threading
import logging
import time


def addresss2nicestring(address):
	#address is a (str,port) tuple from socket.recvfrom() or socket.getpeername()
	#output is something nice such as "192.0.2.7" or "2001:0db8:1::7"
	if address!=None:
		return address[0]
	else:
		return None


class ServeThread(threading.Thread):
	def __init__(self,tcp_server):
		threading.Thread.__init__(self)
		self.tcp_server = tcp_server
	def run(self):
		self.tcp_server.serve_forever()


class ClientInterface(object):
	def __init__(self, port):
		self.logger = logging.getLogger(__name__)
		self.server = TCPCommandLineServer(port,self.process_command)
		self.thread = ServeThread(self.server)
	
	def start(self):
		self.thread.start()
		return True
	
	def stop(self):
		self.server.shutdown()
		self.thread.join()
	
	def process_command(self,command_line):
		self.logger.debug("Got command: %s",command_line)
		if len(command_line)==0:
			self.logger.debug("Commandline was empty")
			return ""
		if command_line=="quit" or command_line=="exit":
			#undocumented command but nice for testing with telnet
			return None
		(command,_,arguments) = command_line.partition(' ')
		if command=="getversion":
			response = self.handle_getversion(arguments)
		elif command=="keepalive":
			response = self.handle_keepalive(arguments)
		elif command=="poll":
			response = self.handle_poll(arguments)
		elif command=="keepalivepoll":
			response = self.handle_keepalivepoll(arguments)
		elif command=="getclusters":
			response = self.handle_getclusters(arguments)
		elif command=="getvaguslist":
			response = self.handle_getvaguslist(arguments)
		elif command=="vagushint":
			response = self.handle_vagushint(arguments)
		else:
			self.logger.info("Got unrecognized command: %s",command_line)
			response = None
		if response==None:
			self.logger.info("Failed command: %s", command_line)
		return response
	
	def handle_getversion(self,arguments):
		return "1\n\n"
	
	def handle_keepalive(self,arguments):
		# cluster : id : timeout [: extrainfo]
		if arguments=="":
			return None
		if len(arguments.split(':'))<3:
			return None
		cluster = arguments.split(':')[0]
		instance_id = arguments.split(':')[1]
		timeout_str = arguments.split(':')[2]
		if len(arguments.split(':'))>2:
			extra_info = arguments.partition(':')[2].partition(':')[2].partition(':')[2]
		else:
			extra_info = None
		
		if len(cluster)==0 or len(cluster)>255:
			return None
		if len(instance_id)==0 or len(instance_id)>255:
			return None
		
		try:
			timeout = int(timeout_str)
		except ValueError, ex:
			return None
		
		if extra_info!=None and len(extra_info)>255:
			return None
		
		timeout = min(max(timeout,Config.instance_timeout_min),Config.instance_timeout_max)
		end_of_life = time.time() + timeout/1000.0
		InstanceRegistry.update_local_instance(cluster,instance_id,end_of_life,extra_info)
		
		return "\n"
	
	def handle_poll(self,arguments):
		# cluster
		if arguments=="":
			return None
		cluster = arguments
		d = InstanceRegistry.get_global_instance_dict(cluster)
		r = ""
		for (k,v) in d.items():
			item = str(k)
			if v[1]:
				item += ":" + v[1]
			r += item + "\n"
		return r + "\n"
	
	def handle_keepalivepoll(self,arguments):
		# cluster : id : timeout [: extrainfo]
		if arguments=="":
			return None
		if len(arguments.split(':'))<3:
			return None
		cluster = arguments.split(':')[0]
		instance_id = arguments.split(':')[1]
		timeout_str = arguments.split(':')[2]
		if len(arguments.split(':'))>2:
			extra_info = arguments.partition(':')[2].partition(':')[2].partition(':')[2]
		else:
			extra_info = None
		
		if len(cluster)==0 or len(cluster)>255:
			return None
		if len(instance_id)==0 or len(instance_id)>255:
			return None
		
		try:
			timeout = int(timeout_str)
		except ValueError, ex:
			return None
		
		if extra_info!=None and len(extra_info)>255:
			return None
		
		end_of_life = time.time() + timeout/1000.0
		InstanceRegistry.update_local_instance(cluster,instance_id,end_of_life,extra_info)
		
		return self.handle_poll(cluster)
	
	def handle_getclusters(self,arguments):
		l = InstanceRegistry.get_cluster_list()
		if len(l)>0:
			return "\n".join(l) + "\n" + "\n"
		else:
			return "\n"
	
	def handle_getvaguslist(self,arguments):
		d = VagusRegistry.get_vagus_dict()
		r=""
		for k,v in d.iteritems():
			addr = v[2][0] if v[2]!=None else ""
			r += "%s:%d:%d:%s\n"%(k,v[0]*1000,v[1]*1000,addr)
		return r+"\n"
	
	def handle_vagushint(self,arguments):
		pass #todo
	

if __name__ == "__main__":
	logging.basicConfig(format='%(asctime)s %(process)d %(levelname)s %(module)s:%(message)s',level=logging.DEBUG)
	ci = ClientInterface(8720)
	ci.start()
	import socket
	
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	s.connect(("localhost",8720))
	
	s.send("getversion\n");
	r = s.recv(1024)
	assert r=="1\n\n"
	
	s.send("getclusters\n")
	r = s.recv(1024)
	assert r=="\n"
	
	s.send("poll giraffes\n")
	r = s.recv(1024)
	print "r=",r
	assert r=="\n"
	
	s.send("keepalive giraffes:1:500\n")
	r = s.recv(1)
	print "r=",r
	s.send("keepalive giraffes:2:1500:durian\n")
	r = s.recv(1)
	print "r=",r
	s.send("poll giraffes\n")
	r = s.recv(1024)
	print "r=",r
	assert len(r.split('\n'))==4
	assert "1" in r
	assert "2" in r
	assert "durian" in r
	assert r.split('\n')[2]==""
	
	s.send("getclusters\n")
	r = s.recv(1024)
	assert r=="giraffes\n"
	
	#test instance timeouts
	time.sleep(0.550)
	s.send("poll giraffes\n")
	r = s.recv(1024)
	print "r=",r
	assert len(r.split("\n"))==3
	
	time.sleep(1.050)
	s.send("poll giraffes\n")
	r = s.recv(1024)
	print "r=",r
	assert r=="\n"
	
	s.close()
	
	print "stopping"
	ci.stop()

