import ConfigParser
import socket
import sys


identity = "uninitialized"
instance_timeout_min = 500
instance_timeout_max = 600000
announcement_interval_min = 500
announcement_interval_max = 10000


def initialize(filename):
	config = ConfigParser.ConfigParser()
	config.read([filename])
	
	global identity
	global instance_timeout_min
	global instance_timeout_max
	global announcement_interval_min
	global announcement_interval_max
	
	if config.has_option("main","identity"):
		identity = config.get("main","identity")
		if identity==None or len(identity)==0:
			identity = socket.gethostname()
	
	if config.has_option("main","instance-timeout-min"):
		instance_timeout_min = config.getint("main","instance-timeout-min")
	if config.has_option("main","instance-timeout-max"):
		instance_timeout_max = config.getint("main","instance-timeout-max")

	if config.has_option("main","announcement-interval-min"):
		announcement_interval_min = config.getint("main","announcement-interval-min")
	if config.has_option("main","announcement-interval-max"):
		announcement_interval_max = config.getint("main","announcement-interval-max")
	
	client_port = config.getint("main","client-port")
	
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

if __name__ == "__main__":
	initialize(sys.argv[1])
