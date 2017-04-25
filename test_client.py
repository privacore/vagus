#!/usr/bin/env python
import sys
import time
import socket

while True:
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	try:
		print "Connecting"
		s.connect(("localhost",12345))
		
		print "Connected"
		while True:
			print "sending keepalive"
			s.send("keepalive giraffes:"+sys.argv[1]+":5000\n")
			time.sleep(1.5)
	except socket.error, ex:
		pass
	finally:
		s.close()
	time.sleep(10)

