class InstanceDict(dict):
	def update(self,instance_identifier,end_of_life,extra_info):
		if instance_identifier in self:
			self[instance_identifier] = (end_of_life,extra_info)
			return False
		else:
			self[instance_identifier] = (end_of_life,extra_info)
			return True
	
	def timeout_expired_instances(self,now):
		any_removed = False
		for k in self.keys():
			if self[k][0] <= now:
				del self[k]
				any_removed = True
		return any_removed


if __name__ == "__main__":
	d = InstanceDict()
	assert 1 not in d
	assert d.update(1,1234,"foo")
	assert 1 in d
	assert d[1][0] == 1234
	assert d[1][1] == "foo"
	assert not d.update(1,12345,"foo")
	assert d.update(2,12345,"boo")

	
	d = InstanceDict()
	assert not d.timeout_expired_instances(10)
	d.update(1,17,"foo")
	d.update(2,42,"boo")
	d.update(3,117,"goo")
	assert not d.timeout_expired_instances(10)
	assert d.timeout_expired_instances(20)
	assert not d.timeout_expired_instances(20)
	assert d.timeout_expired_instances(200)
	assert len(d)==0
