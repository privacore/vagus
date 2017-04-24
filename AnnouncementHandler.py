import struct
import logging

logger = logging.getLogger(__name__)

def process_announcement_datagram(datagram):
	logger.debug("Handling datagram")
	if not datagram:
		return
	if len(datagram)<5+4+1:
		return
	if datagram[0:5]!="vagus":
		return
	(signature,length,message_type) = struct.unpack("!5si",datagam[0:10])
	payload = datagram[10:]
	if length!=len(payload):
		return
	
	logger.debug("Got valid vagus datagram, type=0x%x, length=%d", length,message_type)
	
	if message_type==1:
		process_announcement(payload)
	else:
		logger.info("Got invalid vagus datagram")


def process_announcement(payload):
	pass
