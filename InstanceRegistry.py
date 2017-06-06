from InstanceDict import InstanceDict
import copy
import threading
import time
import logging

local_instances = {}   #cluster->InstanceDict()
global_instances = {}  #cluster->InstanceDict()

registry_lock = threading.Lock()

def noop_change_callback(cluster):
	pass

callback = noop_change_callback

logger = None


def update_local_instance(cluster,instance_identifier,keepalive_lifetime,end_of_life,extra_info):
	global logger
	if logger==None:
		logger = logging.getLogger(__name__)
	
	any_changes = False
	try:
		registry_lock.acquire()
		if not cluster in local_instances:
			local_instances[cluster] = InstanceDict()
		if local_instances[cluster].update(None,instance_identifier,keepalive_lifetime,end_of_life,extra_info):
			any_changes = True
		if not cluster in global_instances:
			global_instances[cluster] = InstanceDict()
		if global_instances[cluster].update(None,instance_identifier,keepalive_lifetime,end_of_life,extra_info):
			any_changes = True
	finally:
		registry_lock.release()
	if any_changes:
		callback(cluster)


def update_nonlocal_instance(source,cluster,instance_identifier,end_of_life,extra_info):
	global logger
	if logger==None:
		logger = logging.getLogger(__name__)
	
	try:
		registry_lock.acquire()
		if not cluster in global_instances:
			global_instances[cluster] = InstanceDict()
		global_instances[cluster].update(source,instance_identifier,None,end_of_life,extra_info)
	finally:
		registry_lock.release()


def get_cluster_list():
	try:
		registry_lock.acquire()
		l = global_instances.keys()
	finally:
		registry_lock.release()
	return l

def get_local_instance_dict(cluster):
	now = time.time()
	try:
		registry_lock.acquire()
		if cluster not in local_instances:
			return InstanceDict()
		removed_instance_ids = local_instances[cluster].timeout_expired_instances(now)
		l = copy.copy(local_instances[cluster])
	finally:
		registry_lock.release()
	if removed_instance_ids:
		logger.info("Instances %s were removed from local registry",removed_instance_ids)
	return l

def get_global_instance_dict(cluster):
	now = time.time()
	try:
		registry_lock.acquire()
		if cluster not in global_instances:
			return InstanceDict()
		b = global_instances[cluster].timeout_expired_instances(now)
		l = copy.copy(global_instances[cluster])
	finally:
		registry_lock.release()
	return l


def set_change_callback(c):
	global callback
	callback = c
