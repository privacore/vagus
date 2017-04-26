import time
import copy
import threading
import Config

vagus_instances = {} #id-> (timestamp,eol)
lock = threading.Lock()


def update_vagus_instance(vagus_id,end_of_life):
	try:
		lock.acquire()
		vagus_instances[vagus_id] = (time.time(),end_of_life)
	finally:
		lock.release()


def expire():
	now = time.time()
	try:
		lock.acquire()
		for k in vagus_instances.keys():
			if vagus_instances[k][1]<now:
				del vagus_instances[k]
	finally:
		lock.release()

def get_vagus_dict():
	expire()
	d = copy.deepcopy(vagus_instances)
	if Config.identity not in d:
		#ensure we are always present
		d[Config.identity] = (time.time(), time.time()+Config.announcement_interval_max*2/1000.0)
	return d
