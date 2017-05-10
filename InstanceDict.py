class Instance(object):
	def __init__(self,instance_identifier,keepalive_lifetime,end_of_life,extra_info):
		self.instance_identifier = instance_identifier
		self.keepalive_lifetime = keepalive_lifetime
		self.end_of_life = end_of_life
		self.extra_info = extra_info
	def __str__(self):
		return str(self.instance_identifier)

class InstanceDict(dict):
	def update(self,instance_identifier,keepalive_lifetime,end_of_life,extra_info):
		i = Instance(instance_identifier,keepalive_lifetime,end_of_life,extra_info)
		if instance_identifier in self:
			self[instance_identifier] = i
			return False
		else:
			self[instance_identifier] = i
			return True
	
	def timeout_expired_instances(self,now):
		any_removed = False
		for k in self.keys():
			if self[k].end_of_life <= now:
				del self[k]
				any_removed = True
		return any_removed
	
	def get_lowest_keepalive_lifetime(self):
		m = None
		for v in self.itervalues():
			if m==None or v.keepalive_lifetime<m:
				m = v.keepalive_lifetime
		return m


if __name__ == "__main__":
	d = InstanceDict()
	assert 1 not in d
	assert d.update(1,1234,5678,"foo")
	assert 1 in d
	assert d[1].keepalive_lifetime == 1234
	assert d[1].end_of_life == 5678
	assert d[1].extra_info == "foo"
	assert not d.update(1,12345,67890,"foo")
	assert d.update(2,12345,67890,"boo")

	
	d = InstanceDict()
	assert not d.timeout_expired_instances(10)
	d.update(1,17,17,"foo")
	d.update(2,42,42,"boo")
	d.update(3,117,117,"goo")
	assert not d.timeout_expired_instances(10)
	assert d.timeout_expired_instances(20)
	assert not d.timeout_expired_instances(20)
	assert d.timeout_expired_instances(200)
	assert len(d)==0
