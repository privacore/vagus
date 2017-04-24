import UDPHandler
import InstanceRegistry
import Config
import logging
import threading
import time
import struct

changed_cv = threading.Condition()
anything_changed = False
thread = None

logger = None

def initialize():
	global logger
	logger = logging.getLogger(__name__)
	logger.debug("@@@")
	InstanceRegistry.set_change_callback(local_instances_changed_callback)
	global thread
	thread = GeneratorThread()
	thread.start()
	logger.debug("@@@")


def local_instances_changed_callback(cluster):
	global anything_changed
	logger.debug("in local_instances_changed_callback():")
	changed_cv.acquire()
	anything_changed = True
	changed_cv.notify()
	changed_cv.release()


class GeneratorThread(threading.Thread):
	def run(self):
		logger.debug("@@@ hurra")
		global anything_changed
		last_send = time.time()
		next_earliest_send = time.time() + Config.announcement_interval_min/1000.0
		next_latest_send = time.time() + Config.announcement_interval_max/1000.0
		while True:
			now = time.time()
			logger.debug("now               = %f",now)
			logger.debug("next_earliest_send= %f",next_earliest_send)
			logger.debug("next_latest_send  = %f",next_latest_send)
			if now < next_earliest_send:
				#enforce minimum sleep
				logger.debug("enforcing minimum interval")
				t = next_earliest_send-now
				logger.debug(" t = %f",t)
				time.sleep(next_earliest_send-now)
			changed_cv.acquire()
			while not anything_changed:
				logger.debug("inside wait loop")
				now = time.time()
				logger.debug("now = %f", now)
				if now>=next_latest_send or anything_changed:
					break
				logger.debug("Waiting for %f",next_latest_send-now)
				changed_cv.wait(next_latest_send-now)
				logger.debug("wait() returned")
				logger.debug("anything_changed=%s",anything_changed)
			anything_changed = False
			changed_cv.release()
			
			self.send_announcements()
			now = time.time()
			next_earliest_send = now + Config.announcement_interval_min/1000.0
			next_latest_send = now + Config.announcement_interval_max/1000.0
			#todo: do timeouts per cluster
			#todo: do instance timeouts
	
	def send_announcements(self):
		logger.debug("Generating announcements")
		for cluster in InstanceRegistry.get_cluster_list():
			self.send_cluster_announcement(cluster,InstanceRegistry.get_local_instance_dict(cluster))
	
	def send_cluster_announcement(self,cluster,instance_dict):
		logger.debug("Generating announcement for cluster %s",cluster)
		message = self.form_announcement_message(cluster,instance_dict)
		UDPHandler.send_announce(message)
	
	def form_announcement_message(self,cluster,instance_dict):
		instance_information = ""
		#struct.pack(...p...) doesn't work (?)
		for (k,v) in instance_dict.items():
			logger.debug("k=%s v=%s",k,v)
			logger.debug("type(k)=%s",type(k))
			logger.debug("len(k)=%d",len(k))
			instance_information += struct.pack("!B",len(k)) + k
			instance_information += struct.pack("!I",int(v[0])) 
			if v[1]:
				instance_information += struct.pack("!B",len(v[1])) + v[1]
		logger.debug("instance_information: %s",hexstring(instance_information))
		announcement_end_of_life = time.time() + (Config.announcement_interval_max*2 / 1000.0)
		length = 5 + 4 + 4 + 1+len(Config.identity) + 1+len(cluster) + len(instance_information)
		message = "vagus"
		message+= struct.pack("!I",length)
		message+= struct.pack("!I",announcement_end_of_life)
		print "type:",type(Config.identity)
		message+= struct.pack("!B",len(Config.identity)) + Config.identity
		message+= struct.pack("!B",len(cluster)) + cluster
		message+= instance_information
		
		return message

def hexstring(s):
	r=""
	for c in s:
		r += "%02x"%ord(c)
	return r

