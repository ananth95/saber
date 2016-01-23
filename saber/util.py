DEFAULT_REGEN = 0.8

MAX_ARATE = 5
CSPEED    = 5
DCSPEED   = 10

class Server:
	def __init__(self, pos, power, maxpow, owner, index):
		self.pos      = pos
		self.reserve  = power
		self.invested = 0
		self.owner    = owner
		# invested + reserve = power
		self._index = index
		self.limit = maxpow
		self.connections = {}

	def strify(self):
		return "%f %f %f %f %f %d" % (self.pos[0], self.pos[1], self.reserve, self.invested, self.limit, self.owner)
	
	def __repr__(self):
		return ("{Own%2d,(%3.3f,%3.3f),res%f,inv%f,lim%f}" % (self.owner, self.pos[0], self.pos[1], self.reserve, self.invested, self.limit))

	def update_pow(self, dr, di):
		self.reserve += dr
		self.invested += di
		return self.reserve
	
	def new_connection(self, v_sid, arate, distance):
		if v_sid in self.connections.keys():
			raise RuntimeError("Already connected to %d from %d. Something wrong with quantum.py" %(v_sid, self.index))
		else:
			self.connections[v_sid] = Connection(self.index, v_sid, arate, distance)

	def update_connection(self, v_sid, arate):
		if v_sid not in self.connections.keys():
			raise RuntimeError("No connection to %d from %d, can't update. First make a connection!" %(v_sid, self.index))

	@property
	# index has no setter
	def index(self):
		return self._index

	@property
	# power has no setter
	def power(self):
		return self.reserve + self.invested

	@property
	# regen_rate has no setter
	def regen_rate(self):
		return DEFAULT_REGEN

class Connection:
	STATE_MAP = {'making': 0, 'connected': 1, 'withdrawing': 2}
	def __init__(self, attacker, victim, arate, distance):
		self.attacker = attacker
		self.victim = victim
		self._arate = arate
		self.state = Connection.STATE_MAP['making']
		# -1 length denotes that the connection is made in "this turn"
		self.length = 0
		self.full_distance = distance

	def strify(self):
		return "%d %d %f" % (self.attacker, self.victim, self.arate)
	
	def __repr__(self):
		return ("{A %d,V %d,rate %f,%s,%f }" % (self.attacker, self.victim, self.arate, self.state, self.length))

	@property
	def arate(self):
		return self._arate

	@arate.setter
	def arate(self, val):
		if val < 0 or val > MAX_ARATE:
			raise RuntimeError("Wrong 'new' attack_rate (%f) Acceptable[0, %f]" % (val, MAX_ARATE))
		else:
			self._arate = val