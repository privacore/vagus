import UDPHandler
import UDPMulticastHandler
import TCPHandler
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

#python's min() returns none on min(...None..)
def min_ignoring_none(a,b):
	if a==None:
		return b
	elif b==None:
		return a
	else:
		return min(a,b)

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
			mktaac = self.min_keepalive_timeout_across_all_clusters()
			effective_announcement_interval_max = min_ignoring_none(Config.announcement_interval_max,mktaac)
			effective_announcement_interval_max = max(Config.announcement_interval_min,effective_announcement_interval_max)
			next_latest_send = now + effective_announcement_interval_max/1000.0
			if mktaac!=None:
				#hackish:
				#  We want to send out announcements so they are received and processed by other vagus instances
				#  before any instances time out, but we have no way of knowing the delay from we send to that is done.
				#If this hack doesn't work then you have to configure announcement-interval-max
				next_latest_send -= 0.050
			#todo: do timeouts per cluster

	def min_keepalive_timeout_across_all_clusters(self):
		m = None
		for cluster in InstanceRegistry.get_cluster_list():
			m2 = InstanceRegistry.get_local_instance_dict(cluster).get_lowest_keepalive_lifetime()
			if m2!=None and m2<Config.announcement_interval_min:
				logger.warn("cluster %s has instances with keepalive-lifetime (%s) less than [main]:announcement-interval-min (%s)",cluster,m2,Config.announcement_interval_min)
			if m==None or m2<m:
				m=m2
		return m
	
	def send_announcements(self):
		logger.debug("Generating announcements")
		for cluster in InstanceRegistry.get_cluster_list():
			self.send_cluster_announcement(cluster,InstanceRegistry.get_local_instance_dict(cluster))
	
	def send_cluster_announcement(self,cluster,instance_dict):
		logger.debug("Generating announcement for cluster %s",cluster)
		message = self.form_announcement_message(cluster,instance_dict)
		UDPHandler.send_announce(message)
		UDPMulticastHandler.send_announce(message)
		TCPHandler.send_announce(message)
	
	def form_announcement_message(self,cluster,instance_dict):
		instance_information = ""
		#struct.pack(...p...) doesn't work (?)
		for (k,v) in instance_dict.items():
			instance_information += struct.pack("!B",len(k)) + k
			instance_information += struct.pack("!Q",int(v.end_of_life*1000))
			if v.extra_info:
				instance_information += struct.pack("!B",len(v.extra_info)) + v.extra_info
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
