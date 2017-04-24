from collections import OrderedDict
import ConfigParser
import socket
import sys
import string


class Container(object):
	pass
identity = "uninitialized"
instance_timeout_min = 500
instance_timeout_max = 600000
announcement_interval_min = 500
announcement_interval_max = 10000
client_port = 8720
udp = Container()
udp.port = 8721
udp.peer=[]
udp.broadcast=[]
udp_multicast = Container()
udp_multicast.port = 8722
udp_multicast.multicast = []
tcp = Container()
tcp.port = 8721


#copy-pasta from stackoverflow, author: user2185338
class MultiOrderedDict(OrderedDict):
	def __setitem__(self, key, value):
		if key in self:
			if isinstance(value, list):
				self[key].extend(value)
				return
			elif isinstance(value,str):
				return # ignore conversion list to string (line 554)
		super(MultiOrderedDict, self).__setitem__(key, value)


def parse_udp_multicast(s):
	#accept interface:ip
	#transform into tuple (interface,ip-str)
	if ":" not in s:
		return None
	(first,_,second) = s.partition(':')
	#interface must '*' or start with a letter
	if first!='*' and (first[0] not in string.ascii_letters):
		return None
	if "." in second and ":" in second:
		return None
	elif (":" not in second) and ("." not in second):
		return None
	return (first,second)

def validate_ip(s):
	#Accept dotted-quad IPv4, or IPv6.
	#Simple but we do a bit of validation for common mistakes such as specifying the port or using a hostname
	if "." in s and ":" in s:
		return None
	elif (":" not in s) and ("." not in s):
		return None
	if ":" not in s:
		#ipv4, easy check for hostname
		if s[0] in string.ascii_letters:
			return None
		if s[-1] in string.ascii_letters:
			return None
	return s

def valudate_broadcast(s):
	#ifname or address
	if "." in s:
		#addr, must be dotted-quad
		if len(s.split("."))!=4:
			return None
	else:
		#ifname, must start with letter or be "*"
		if s!='*' and (s[0] not in string.ascii_letters):
			return None
	return s

def initialize(filename):
	config = ConfigParser.RawConfigParser(dict_type=MultiOrderedDict)
	config.read([filename])
	
	global identity
	global instance_timeout_min
	global instance_timeout_max
	global announcement_interval_min
	global announcement_interval_max
	global client_port
	
	if config.has_option("main","identity"):
		identity = config.get("main","identity")[0]
		if identity==None or len(identity)==0:
			identity = socket.gethostname()
	else:
		identity = socket.gethostname()
	
	if config.has_option("main","instance-timeout-min"):
		instance_timeout_min = int(config.get("main","instance-timeout-min")[0])
	if config.has_option("main","instance-timeout-max"):
		instance_timeout_max = int(config.get("main","instance-timeout-max")[0])

	if config.has_option("main","announcement-interval-min"):
		announcement_interval_min = int(config.get("main","announcement-interval-min")[0])
	if config.has_option("main","announcement-interval-max"):
		announcement_interval_max = int(config.get("main","announcement-interval-max")[0])
	
	client_port = int(config.get("main","client-port")[0])
	
	#validate
	if instance_timeout_min<0:
		print >>sys.stderr, "instance-timeout-min < 0"
		return False
	if instance_timeout_max < instance_timeout_min:
		print >>sys.stderr, "instance-timeout-max < instance-timeout-min"
		return False
	
	if announcement_interval_min<0:
		print >>sys.stderr, "announcement-interval-min < 0"
		return False
	if announcement_interval_max < announcement_interval_min:
		print >>sys.stderr, "announcement-interval-max < announcement-interval-min"
		return False
	
	if client_port<=0 or client_port>=65535:
		print >>sys.stderr, "client-port outside 1..65534 range"
		return False

	if config.has_section("udp"):
		global udp
		if config.has_option("udp","port"):
			udp.port = int(config.get("udp","port")[0])
		if config.has_option("udp","peer"):
			tmp = config.get("udp","peer")
			udp.peer=[]
			if type(tmp)==list:
				for tmp2 in tmp:
					p = validate_ip(tmp2)
					if p==None:
						print >>sys.stderr, "Unhandled udp peer:",tmp2
						return False
					udp.peer.append(p)
			else:
				p = validate_ip(tmp)
				if p==None:
					print >>sys.stderr, "Unhandled udp peer:",tmp
					return False
				udp.peer.append(p)
		if config.has_option("udp","broadcast"):
			tmp = config.get("udp","broadcast")
			udp.broadcast=[]
			if type(tmp)==list:
				for tmp2 in tmp:
					p = valudate_broadcast(tmp2)
					if p==None:
						print >>sys.stderr, "Unhandled udp broadcast:",tmp2
						return False
					udp.broadcast.append(p)
			else:
				p = valudate_broadcast(tmp)
				if p==None:
					print >>sys.stderr, "Unhandled udp broadcast:",tmp
					return False
				udp.broadcast.append(p)
	
	if config.has_section("udp-multicast"):
		global udp_multicast
		if config.has_option("udp-multicast","port"):
			udp_multicast.port = int(config.get("udp-multicast","port")[0])
		if config.has_option("udp-multicast","multicast"):
			tmp = config.get("udp-multicast","multicast")
			udp_multicast.multicast=[]
			if type(tmp)==list:
				for tmp2 in tmp:
					p = parse_udp_multicast(tmp2)
					if p==None:
						print >>sys.stderr, "Unhandled udp multicast:",tmp2
						return False
					udp_multicast.multicast.append(p)
			else:
				p = parse_udp_multicast(tmp)
				if p==None:
					print >>sys.stderr, "Unhandled udp multicast:",tmp
					return False
				udp_multicast.multicast.append(p)
	
	if config.has_section("tcp"):
		global tcp
		if config.has_option("tcp","port"):
			tcp.port = int(config.get("tcp","port")[0])
		if config.has_option("tcp","peer"):
			tmp = config.get("tcp","peer")
			tcp.peer=[]
			if type(tmp)==list:
				for tmp2 in tmp:
					p = validate_ip(tmp2)
					if p==None:
						print >>sys.stderr, "Unhandled tcp peer:",tmp2
						return False
					tcp.peer.append(p)
			else:
				p = validate_ip(tmp)
				if p==None:
					print >>sys.stderr, "Unhandled tcp peer:",tmp
					return False
				tcp.peer.append(p)
	

if __name__ == "__main__":
	initialize(sys.argv[1])
	assert len(udp.broadcast)>0
