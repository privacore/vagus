import InstanceRegistry
import Config
import struct
import logging
import time

logger = None



def process_message(message):
	global logger
	if not logger:
		logger = logging.getLogger(__name__)
	logger.debug("Handling message")
	if not message:
		return
	if len(message)<5+4+1:
		return
	if message[0:5]!="vagus":
		return
	(signature,length,message_type) = struct.unpack("!5siB",message[0:10])
	payload = message[10:]
	if length!=len(payload):
		return
	
	logger.debug("Got valid vagus message, type=0x%x, length=%d", length,message_type)
	
	if message_type==1:
		process_announcement(payload)
	else:
		logger.info("Got invalid vagus message")


def process_announcement(payload):
	if len(payload)<8:
		logger.debug("Got invalid payload")
		return
	p = 0
	announcement_end_of_life = struct.unpack("!I",payload[p:p+4])
	p += 4
	vagus_id_length = struct.unpack("!B",payload[p:p+1])
	p += 1
	if len(payload)-p < vagus_id_length:
		logger.debug("Got invalid payload")
		return
	vagus_id = payload[p:p+vagus_id_length]
	p += vagus_id_length
	cluster_id_length = struct.unpack("!B",payload[p:p+1])
	p += 1
	if len(payload)-p < cluster_id_length:
		logger.debug("Got invalid payload")
		return
	cluster_id = payload[p:p+cluster_id_length]
	p += cluster_id_length
	instance_information = []
	while p<len(payload):
		if len(payload)-p < 6:
			logger.debug("Got invalid payload")
			return
		instance_id_length = struct.unpack("!B",payload[p:p+1])
		p += 1
		if len(payload)-p < instance_id_length:
			logger.debug("Got invalid payload")
			return
		instance_id = payload[p:p+instance_id_length]
		p += instance_id_length
		if len(payload)-p < 4+1:
			logger.debug("Got invalid payload")
			return
		instance_end_of_life = struct.unpack("!I",payload[p:p+4])
		extra_information_length = struct.unpack("!B",payload[p:p+1])
		p += 1
		if len(payload)-p < extra_information_length:
			logger.debug("Got invalid payload")
			return
		extra_information = payload[p:p+extra_information_length]
		p += extra_information_length
		if extra_information=="":
			extra_information = None
		instance_information.append((instance_id,end_of_life,extra_information))
	logger.debug("Got announcement from %s, %d instances", vagus_id, len(instance_information))
	
	if announcement_end_of_life < time.time():
		logger.info("Got expired announcement from %s", vagus_id)
		return
	
	if vagus_id==Config.identity:
		logger.debug("Got announcement from ourselves")
		return
	
	#update the global registry
	for i in instance_information:
		InstanceRegistry.update_nonlocal_instance(i[0],i[1],i[2])
