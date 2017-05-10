from InstanceDict import InstanceDict
import copy
import threading
import time

local_instances = {}   #cluster->InstanceDict()
global_instances = {}  #cluster->InstanceDict()

registry_lock = threading.Lock()

def noop_change_callback(cluster):
	pass

callback = noop_change_callback



def update_local_instance(cluster,instance_identifier,keepalive_lifetime,end_of_life,extra_info):
	any_changes = False
	try:
		registry_lock.acquire()
		if not cluster in local_instances:
			local_instances[cluster] = InstanceDict()
		if local_instances[cluster].update(instance_identifier,keepalive_lifetime,end_of_life,extra_info):
			any_changes = True
		if not cluster in global_instances:
			global_instances[cluster] = InstanceDict()
		if global_instances[cluster].update(instance_identifier,keepalive_lifetime,end_of_life,extra_info):
			any_changes = True
	finally:
		registry_lock.release()
	if any_changes:
		callback(cluster)


def update_nonlocal_instance(cluster,instance_identifier,end_of_life,extra_info):
	try:
		registry_lock.acquire()
		if not cluster in global_instances:
			global_instances[cluster] = InstanceDict()
		global_instances[cluster].update(instance_identifier,None,end_of_life,extra_info)
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
			return {}
		local_instances[cluster].timeout_expired_instances(now)
		l = copy.deepcopy(local_instances[cluster])
	finally:
		registry_lock.release()
	return l

def get_global_instance_dict(cluster):
	now = time.time()
	try:
		registry_lock.acquire()
		if cluster not in global_instances:
			return {}
		b = global_instances[cluster].timeout_expired_instances(now)
		l = copy.deepcopy(global_instances[cluster])
	finally:
		registry_lock.release()
	return l


def set_change_callback(c):
	global callback
	callback = c
