#!/usr/bin/env python
import sys
import time
import socket

while True:
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	try:
		print "Connecting"
		s.connect(("localhost",8720))
		
		print "Connected"
		while True:
			print "sending keepalive"
			if len(sys.argv)<=3:
				s.send("keepalive "+sys.argv[1]+":"+sys.argv[2]+":5000\n")
			else:
				s.send("keepalive "+sys.argv[1]+":"+sys.argv[2]+":5000:"+sys.argv[3]+"\n")
			time.sleep(1.5)
	except socket.error, ex:
		pass
	finally:
		s.close()
	time.sleep(10)

