#!/usr/bin/python

# Based on https://gist.github.com/provegard/1536682, which was
# Based on getifaddrs.py from pydlnadms [http://code.google.com/p/pydlnadms/].
# Only tested on Linux!

from socket import AF_INET, AF_INET6, inet_ntop
from ctypes import (
	Structure, Union, POINTER,
	pointer, get_errno, cast,
	c_ushort, c_byte, c_void_p, c_char_p, c_uint, c_int, c_uint16, c_uint32
)
import ctypes.util
import ctypes

IFF_UP = 0x1               # Interface is up.
IFF_BROADCAST = 0x2        # Broadcast address valid.
IFF_DEBUG = 0x4            # Turn on debugging.
IFF_LOOPBACK = 0x8         # Is a loopback net.
IFF_POINTOPOINT = 0x10     # Interface is point-to-point link.
IFF_NOTRAILERS = 0x20      # Avoid use of trailers.
IFF_RUNNING = 0x40         # Resources allocated.
IFF_NOARP = 0x80           # No address resolution protocol.
IFF_PROMISC = 0x100        # Receive all packets.

IFF_ALLMULTI = 0x200       # Receive all multicast packets.

IFF_MASTER = 0x400         # Master of a load balancer.
IFF_SLAVE = 0x800          # Slave of a load balancer.

IFF_MULTICAST = 0x1000     # Supports multicast.

IFF_PORTSEL = 0x2000       # Can set media type.
IFF_AUTOMEDIA = 0x4000     # Auto media select active.
IFF_DYNAMIC = 0x8000       # Dialup device with changing addresses.

IFF_LOWER_UP =   0x10000   # driver signals L1 up
IFF_DORMANT =    0x20000   # driver signals dormant

IFF_ECHO =       0x40000    # echo sent packets


def ifa_flags_to_string(flags):
	if flags==0:
		return "0"
	s=""
	if flags&IFF_UP:
		s += ",up"
		flags -= IFF_UP
	if flags&IFF_BROADCAST:
		s += ",broadcast"
		flags -= IFF_BROADCAST
	if flags&IFF_DEBUG:
		s += ",debug"
		flags -= IFF_DEBUG
	if flags&IFF_LOOPBACK:
		s += ",loopback"
		flags -= IFF_LOOPBACK
	if flags&IFF_POINTOPOINT:
		s += ",p2p"
		flags -= IFF_POINTOPOINT
	if flags&IFF_NOTRAILERS:
		s += ",notrailers"
		flags -= IFF_NOTRAILERS
	if flags&IFF_RUNNING:
		s += ",running"
		flags -= IFF_RUNNING
	if flags&IFF_NOARP:
		s += ",noarp"
		flags -= IFF_NOARP
	if flags&IFF_PROMISC:
		flags += ",promisc"
		flags -= IFF_PROMISC
	if flags&IFF_ALLMULTI:
		s += ",allmulti"
		flags -= IFF_ALLMULTI
	if flags&IFF_MASTER:
		s += ",master"
		flags -= IFF_MASTER
	if flags&IFF_SLAVE:
		s += ",slave"
		flags -= IFF_SLAVE
	if flags&IFF_MULTICAST:
		s += ",multicast"
		flags -= IFF_MULTICAST
	if flags&IFF_PORTSEL:
		s += ",portsel"
		flags -= IFF_PORTSEL
	if flags&IFF_AUTOMEDIA:
		s += ",automedia"
		flags -= IFF_AUTOMEDIA
	if flags&IFF_DYNAMIC:
		s += ",dynamic"
		flags -= IFF_DYNAMIC
	if flags&IFF_LOWER_UP:
		s += ",lower_up"
		flags -= IFF_LOWER_UP
	if flags&IFF_DORMANT:
		s += ",dormant"
		flags -= IFF_DORMANT
	if flags&IFF_ECHO:
		s += ",echo"
		flags -= IFF_ECHO
	if flags!=0:
		s += ",0x%x"%flags
	if len(s)>0:
		return s[1:]
	else:
		return ""

class struct_sockaddr(Structure):
	_fields_ = [
		('sa_family', c_ushort),
		('sa_data', c_byte * 14),]

class struct_sockaddr_in(Structure):
	_fields_ = [
		('sin_family', c_ushort),
		('sin_port', c_uint16),
		('sin_addr', c_byte * 4)]

class struct_sockaddr_in6(Structure):
	_fields_ = [
		('sin6_family', c_ushort),
		('sin6_port', c_uint16),
		('sin6_flowinfo', c_uint32),
		('sin6_addr', c_byte * 16),
		('sin6_scope_id', c_uint32)]

class union_ifa_ifu(Union):
	_fields_ = [
		('ifu_broadaddr', POINTER(struct_sockaddr)),
		('ifu_dstaddr', POINTER(struct_sockaddr)),]

class struct_ifaddrs(Structure):
	pass
struct_ifaddrs._fields_ = [
	('ifa_next', POINTER(struct_ifaddrs)),
	('ifa_name', c_char_p),
	('ifa_flags', c_uint),
	('ifa_addr', POINTER(struct_sockaddr)),
	('ifa_netmask', POINTER(struct_sockaddr)),
	('ifa_ifu', union_ifa_ifu),
	('ifa_data', c_void_p),]

libc = ctypes.CDLL(ctypes.util.find_library('c'))

def ifap_iter(ifap):
	ifa = ifap.contents
	while True:
		yield ifa
		if not ifa.ifa_next:
			break
		ifa = ifa.ifa_next.contents

def getfamaddr(sa):
	family = sa.sa_family
	addr = None
	if family == AF_INET:
		sa = cast(pointer(sa), POINTER(struct_sockaddr_in)).contents
		addr = inet_ntop(family, sa.sin_addr)
	elif family == AF_INET6:
		sa = cast(pointer(sa), POINTER(struct_sockaddr_in6)).contents
		addr = inet_ntop(family, sa.sin6_addr)
	return family, addr

class NetworkInterfaceAddress(object):
	def __init__(self,ifa):
		self.name = ifa.ifa_name.decode("UTF-8")
		self.flags = ifa.ifa_flags
		if ifa.ifa_addr:
			(self.addr_family,self.addr) = getfamaddr(ifa.ifa_addr.contents)
		else:
			(self.addr_family,self.addr) = (None,None)
		if ifa.ifa_netmask:
			self.netmask = getfamaddr(ifa.ifa_netmask.contents)
		else:
			self.netmask = None
		self.broadcast_addr = None
		if self.flags&IFF_BROADCAST:
			if ifa.ifa_ifu.ifu_broadaddr:
				(_,self.broadcast_addr) = getfamaddr(ifa.ifa_ifu.ifu_broadaddr.contents)
			else:
				#broadcast flag set on interface, but no broadcast address provided. This happens eg. for AF_PACKET family
				pass
	
	def __str__(self):
		if self.addr:
			if self.broadcast_addr:
				return self.name + ":flags=" + ifa_flags_to_string(self.flags) + ":family="+str(self.addr_family) + ":addr=" + self.addr + ":broadcast=" + self.broadcast_addr
			else:
				return self.name + ":flags=" + ifa_flags_to_string(self.flags) + ":family="+str(self.addr_family) + ":addr=" + self.addr
		else:
			return self.name + ":flags=" + ifa_flags_to_string(self.flags) + ":family="+str(self.addr_family)
	
def get_network_interfaces():
	ifap = POINTER(struct_ifaddrs)()
	result = libc.getifaddrs(pointer(ifap))
	if result != 0:
		raise OSError(get_errno())
	del result
	try:
		retval = []
		for ifa in ifap_iter(ifap):
			retval.append(NetworkInterfaceAddress(ifa))
		return retval
	finally:
		libc.freeifaddrs(ifap)

if __name__ == '__main__':
	for ni in get_network_interfaces():
		print ni
