import UDPHandler
import UDPMulticastHandler
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
	InstanceRegistry.set_change_callback(local_instances_changed_callback)
	global thread
	thread = GeneratorThread()
	thread.start()
	return True


def local_instances_changed_callback(cluster):
	global anything_changed
	logger.debug("in local_instances_changed_callback():")
	changed_cv.acquire()
	anything_changed = True
	changed_cv.notify()
	changed_cv.release()


class GeneratorThread(threading.Thread):
	def run(self):
		global anything_changed
		last_send = time.time()
		next_earliest_send = time.time() + Config.announcement_interval_min/1000.0
		next_latest_send = time.time() + Config.announcement_interval_max/1000.0
		while True:
			now = time.time()
			if now < next_earliest_send:
				#enforce minimum sleep
				#logger.debug("enforcing minimum interval")
				t = next_earliest_send-now
				time.sleep(next_earliest_send-now)
			changed_cv.acquire()
			while not anything_changed:
				now = time.time()
				if now>=next_latest_send or anything_changed:
					break
				changed_cv.wait(next_latest_send-now)
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
		UDPMulticastHandler.send_announce(message)
	
	def form_announcement_message(self,cluster,instance_dict):
		instance_information = ""
		#struct.pack(...p...) doesn't work (?)
		for (k,v) in instance_dict.items():
			instance_information += struct.pack("!B",len(k)) + k
			instance_information += struct.pack("!Q",int(v[0]*1000)) 
			if v[1]:
				instance_information += struct.pack("!B",len(v[1])) + v[1]
			else:
				instance_information += struct.pack("!B",0)
		announcement_end_of_life = time.time() + (Config.announcement_interval_max*2 / 1000.0)
		length = 5 + 4 + 1 + 4 + 1+len(Config.identity) + 1+len(cluster) + len(instance_information)
		message = "vagus"
		message+= struct.pack("!I",length)
		message+= struct.pack("!B",1) #type=announcement
		message+= struct.pack("!I",announcement_end_of_life)
		message+= struct.pack("!B",len(Config.identity)) + Config.identity
		message+= struct.pack("!B",len(cluster)) + cluster
		message+= instance_information
		
		return message
