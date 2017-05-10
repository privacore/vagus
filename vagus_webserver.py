#!/usr/bin/env python
import BaseHTTPServer
from BaseHTTPServer import  HTTPServer
from SocketServer import ThreadingMixIn
import argparse
import logging
import logging.config
import socket
import urlparse
import cgi
import time


def do_command(cmd):
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	try:
		s.connect(("localhost",8720))
		s.send(cmd+"\n")
		result = ""
		while True:
			r = s.recv(1000000)
			if len(r)==0: #socket closed, but we don't expect that
				return None
			result += r
			if result=="\n" or (len(result)>=2 and result[-2:]=="\n\n"):
				break
		return result
	except socket.error, ex:
		logger.debug("Got exception when trying to talk to vagus: %s",ex)
		pass
	finally:
		s.close()
	return None


def get_cluster_list():
	r = do_command("getclusters")
	if not r or len(r)==0:
		return None
	if r=="\n":
		return []
	return r.split('\n')[0:-2]

def get_instance_list(cluster_id):
	r = do_command("poll %s"%cluster_id)
	if not r or len(r)==0:
		return None
	if r=="\n":
		return []
	#do we want to split/parse into instance-id + extra_information? Nah...
	return r.split('\n')[0:-2]

def get_vagus_list():
	r = do_command("getvaguslist")
	if not r or len(r)==0:
		return None
	if r=="\n":
		return []
	#parse into id+lastseen+timeout
	l = []
	for line in r.split("\n"):
		if len(line.split(":"))>=4:
			(vagus_id,last_seen,end_of_life) = line.split(":")[0:3]
			address = line.partition(':')[2].partition(':')[2].partition(':')[2]
			last_seen = int(last_seen)
			end_of_life = int(end_of_life)
			l.append((vagus_id,last_seen,end_of_life,address))
	return l


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
	def log_message(self,format,*args):
		logger.info("%s" % (format%args))

	def do_GET(self):	
		parsed_url = urlparse.urlparse(self.path)
		parameters = cgi.parse_qs(parsed_url.query)
		#print "parameters=",parameters
		if parsed_url.path.find("..")!=-1:
			self.send_response(404)
			self.end_headers()
			return
		if parsed_url.path=="/":
			return self.serve_root()
		# /cluster/$cluster_id$
		s = parsed_url.path.split("/")
		if len(s)==3 and s[1]=="cluster":
			return self.serve_cluster(s[2])
		self.send_response(404)
		self.end_headers()
	
	def serve_vaugs_talk_error(self,msg):
		self.send_response(500)
		self.send_header("Content-type", "text/html; charset=utf-8")
		self.end_headers()
		print >>self.wfile, '<html>'
		print >>self.wfile, '<body>'
		print >>self.wfile, '<p>%s</p>'%msg
		print >>self.wfile, '</body>'
		print >>self.wfile, '</html>'
	
	def serve_root(self):
		cluster_list = get_cluster_list()
		if cluster_list==None:
			return self.serve_vaugs_talk_error("Could not get cluster list from vagus")
		vagus_list = get_vagus_list()
		if vagus_list==None:
			return self.serve_vaugs_talk_error("Could not get vagus list from vagus")
		
		self.send_response(200)
		self.send_header("Content-type", "text/html; charset=utf-8")
		self.send_header("cache-control","max-age=0")
		self.end_headers()
		print >>self.wfile, '<html>'
		print >>self.wfile, '<head>'
		print >>self.wfile, '<title>Vagus: Overview</title>'
		print >>self.wfile, '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>'
		#print >>self.wfile, '<link rel="stylesheet" type="text/css" href="default.css" title="Default"/>'
		print >>self.wfile, '</head>'
		print >>self.wfile, '<body>'
		
		print >>self.wfile, '<h1>Known clusters</h1>'
		print >>self.wfile, '<ul>'
		for cluster in cluster_list:
			print >>self.wfile, '<li><a href="/cluster/%s">%s</a></li>'%(cluster,cluster)
		print >>self.wfile, '</ul>'
			
		print >>self.wfile, '<h1>Known Vagus processes</h1>'
		print >>self.wfile, '<table>'
		print >>self.wfile, '    <tr><th>Identity</th><th>Last seen</th><th>end-of-life</th><th>Most recent address</th></tr>'
		for vagus in vagus_list:
			print >>self.wfile, '    <tr>'
			print >>self.wfile, '        <td>%s</td>'%vagus[0]
			last_seen_str = time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(vagus[1]/1000))
			print >>self.wfile, '        <td>%s</td>'%last_seen_str
			end_of_life_str = time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(vagus[2]/1000))
			print >>self.wfile, '        <td>%s</td>'%end_of_life_str
			print >>self.wfile, '        <td>%s</td>'%vagus[3]
			print >>self.wfile, '    </tr>'
		print >>self.wfile, '</table>'
			
		print >>self.wfile, '</body>'
		print >>self.wfile, '</html>'
	
	def serve_cluster(self,cluster_id):
		instance_list = get_instance_list(cluster_id)
		if instance_list==None:
			return self.serve_vaugs_talk_error("Could not get instance list from vagus")
		instance_list.sort()
		
		self.send_response(200)
		self.send_header("Content-type", "text/html; charset=utf-8")
		self.send_header("cache-control","max-age=0")
		self.end_headers()
		print >>self.wfile, '<html>'
		print >>self.wfile, '<head>'
		print >>self.wfile, '<title>Vagus: instances in %s</title>'%(cluster_id)
		print >>self.wfile, '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>'
		#print >>self.wfile, '<link rel="stylesheet" type="text/css" href="default.css" title="Default"/>'
		print >>self.wfile, '</head>'
		print >>self.wfile, '<body>'
		
		print >>self.wfile, '<h1>Alive instances (%d)</h1>'%(len(instance_list))
		print >>self.wfile, '<ul>'
		for instance in instance_list:
			print >>self.wfile, '<li>%s</li>'%(instance)
		print >>self.wfile, '</ul>'
			
		print >>self.wfile, '</body>'
		print >>self.wfile, '</html>'
	


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	"""Handle requests in a separate thread."""
	pass


parser = argparse.ArgumentParser(description="Vagus web interface")
parser.add_argument("--loggingconf",type=str,default="logging.dev.conf")
parser.add_argument("--port",type=int,default=8724)
args=parser.parse_args()


logging.config.fileConfig(args.loggingconf)

logger = logging.getLogger(__name__)
logger.info("vagus_webserver starting")

httpd = ThreadedHTTPServer(("", args.port), Handler)
logger.info("vagus_webserver ready")
httpd.serve_forever()

