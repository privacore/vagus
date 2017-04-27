import Config
import getifaddrs
import AnnouncementHandler
import socket
import logging
import string
import threading
import struct
import select


#Some multicast groups are per-network-segment and require distinct sockets bound to an address
#so we have to keep a list of sockets and also which multicast addresses/destinations to use on it.
#also, IPv4 and IPv6 are sufficiently different so we have two sets

multicast_socket_ipv4 = []  # [(socket,dst)]
multicast_socket_ipv6 = []  # [(socket,dst)]
handler_thread = None
logger = None


def initialize():
	global logger
	logger = logging.getLogger(__name__)
	if len(Config.udp_multicast.multicast)==0:
		logger.info("Multicast not configured")
		return True
	if Config.udp_multicast.port==0:
		logger.info("Multicast disabled with port=0")
		return True
	
	global multicast_socket_ipv4
	global multicast_socket_ipv6
	#Go through the multicast specifications
	ifaddrs = getifaddrs.get_network_interfaces()
	for mc in Config.udp_multicast.multicast:
		(if_name,addr) = mc
		if '.' in addr:
			#IPv4
			if not setup_ipv4_multicast_socket(ifaddrs,if_name,addr):
				return False
		elif ':' in addr:
			#IPv6
			if not setup_ipv6_multicast_socket(ifaddrs,if_name,addr):
				return False
		else:
			logger.warn("non-IPv4 non-IPV6 address slipped through configuration: %s", addr)
			return False
	
	if len(multicast_socket_ipv4)==0 and len(multicast_socket_ipv6)==0:
		logger.info("No multicast addresses (did you reference a non-existing interface?)")
		return True
	
	global handler_thread
	handler_thread = UDPMulticastHandlerThread()
	handler_thread.start()
	
	
	return True


def setup_ipv4_multicast_socket(ifaddrs, if_name, addr):
	#todo: if_name ignored
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind(("", Config.udp_multicast.port))
	
	s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, Config.udp_multicast.ttl)
	s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
	
	mreq = struct.pack("4sl", socket.inet_aton(addr), socket.INADDR_ANY)
	
	s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
	
	s.setblocking(0)
	
	multicast_socket_ipv4.append((s,addr))
	
	return True


def setup_ipv6_multicast_socket(ifaddrs, if_name, addr):
	#todo: if_name ignored
	s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind(("", Config.udp_multicast.port))
	
	s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, Config.udp_multicast.ttl)
	s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 0)
	
	mreq = struct.pack("16s16s", socket.inet_pton(socket.AF_INET6,addr), chr(0)*16)
	
	s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
	
	s.setblocking(0)
	
	multicast_socket_ipv6.append((s,addr))
	
	return True


class UDPMulticastHandlerThread(threading.Thread):
	def run(self):
		rlist = []
		for (s,addr) in multicast_socket_ipv4:
			rlist.append(s)
		for (s,addr) in multicast_socket_ipv6:
			rlist.append(s)
		while True:
			(r,_,_) = select.select(rlist,[],[])
			for s in r:
				(datagram,address) = s.recvfrom(65535)
				logger.debug("Got datagram from %s",address)
				AnnouncementHandler.process_message(datagram)


def send_announce(datagram):
	if len(datagram)>65507:
		logger.debug("Datagram too large")
		return
	for (s,addr) in multicast_socket_ipv4:
		s.sendto(datagram,(addr,Config.udp_multicast.port))
	for (s,addr) in multicast_socket_ipv6:
		s.sendto(datagram,(addr,Config.udp_multicast.port))
