import Config
import getifaddrs
import AnnouncementHandler
import socket
import logging
import string
import threading


#broadcast configuration cases:
# 1: broadcast: *
# 2: broadcast: eth0
# 3: broadcast: 10.0.0.255
# 4: broadcast: enp5s0:10.0.1.255
#which results in these actions
# 1: single unbound socket, send to 255.255.255.255
# 2: one of more sockets bound to nets on that interface, sending to whatever broadcast address is appropriate
# 3: single unbound socket, send to 10.0.0.255
# 4: one of more sockets bound to nets on that interface, sending to that broadcast address

broadcast_socket = None
broadcast_addresses = []
unicast_socket = None
handler_thread = None
logger = None

def initialize():
	global logger
	logger = logging.getLogger(__name__)
	if len(Config.udp.peer)==0 and len(Config.udp.broadcast)==0:
		logger.info("Broadcasts not configured")
		return True
	if Config.udp.port==0:
		logger.info("Broadcasts disabled with port=0")
		return True
	
	
	#Go through the broadcast specifications
	ifaddrs = getifaddrs.get_network_interfaces()
	global broadcast_addresses
	broadcast_addresses = []
	for b in Config.udp.broadcast:
		if b=="*":
			#global broadcast
			broadcast_addresses.append("255.255.255.255")
		elif b[0] in string.ascii_letters:
			#ifname
			if_name = b
			for ifa in ifaddrs:
				if ifa.name==if_name and ifa.flags&getifaddrs.IFF_BROADCAST and ifa.broadcast_addr:
					broadcast_addresses.append(ifa.broadcast_addr)
		else:
			#addr
			broadcast_addresses.append(b)
	
	logger.debug("Broadcast addresses: %s",broadcast_addresses)
	
	if len(Config.udp.broadcast)!=0 and len(broadcast_addresses)==0:
		logger.info("No broadcast addresses (did you reference a non-existing interface?)")
		return True
	
	#first create a wildcard socket, bound only to the port.
	global broadcast_socket
	broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  
	broadcast_socket.bind(("", Config.udp.port))
	
	#then create an unbound IPv6 socket for unicasts
	global unicast_socket
	unicast_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
	
	global handler_thread
	handler_thread = UDPHandlerThread()
	handler_thread.start()
	
	return True


class UDPHandlerThread(threading.Thread):
	def run(self):
		while True:
			datagram = broadcast_socket.recv(65535)
			logger.debug("Got datagram")
			AnnouncementHandler.process_message(datagram)


def send_announce(datagram):
	if broadcast_socket:
		for addr in broadcast_addresses:
			broadcast_socket.sendto(datagram,(addr,Config.udp.port))
	if unicast_socket:
		for addr in Config.udp.peer:
			logger.debug("Sending unicast to %s",addr)
			#grumble, apparently pythons sendto() doesn't handle ipv6-mapped-ipv4 directly
			if ":" in addr:
				unicast_socket.sendto(datagram,(addr,Config.udp.port))
			else:
				unicast_socket.sendto(datagram,("::ffff:"+addr,Config.udp.port))


if __name__ == "__main__":
	logging.basicConfig(format='%(asctime)s %(process)d %(levelname)s %(module)s:%(message)s',level=logging.DEBUG)
	Config.initialize("vagus.ini")
	initialize()
	send_announce("foo")
	print "done"
