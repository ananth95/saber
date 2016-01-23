import random
import map_util
import util

STATE_MAP = util.Connection.STATE_MAP
VALID_ORDERS = {'a':('attack', 3),   # from, to, rate
				'w':('withdraw', 3), # from, to, split
				'u':('update', 3)}   # from, to, rate
class Game:
	def __init__(self, options):
		# create map and get bot_count, server_count, etc from map_data
		self.mapfile = options["map"]
		self.map          = map_util.Map(self.mapfile)
		self.bot_count    = self.map.bot_count
		self.server_count = self.map.server_count

		self.turntime = options["turntime"]
		self.loadtime = options["loadtime"]
		self.base_dir = options["base_dir"]

		util.DEFAULT_REGEN = options["regen"]
		util.MAX_ARATE     = options["max_arate"]
		util.CSPEED        = options["cspeed"]
		util.DCSPEED       = options["dcspeed"]
		self.amult         = options["amult"]

	def start_game(self):
		self.Clusters = {}
		self.Servers = []
		sid = 0
		for owner in self.map.clusters.keys():
			for server in self.map.clusters[owner]:
				self.Servers.append(util.Server(server["coord"], server["power"], server["limit"], server["owner"], sid))
				if server["owner"] in self.Clusters.keys():
					self.Clusters[server["owner"]].append(sid)
				else:
					self.Clusters[server["owner"]] = [sid]
				sid += 1

		self.turn = 0
		self.scores = [0] * self.bot_count
		self.active = [True] * self.bot_count
		self.killed = [False] * self.bot_count # if True, it denotes that a bot malfunctioned and was killed by the system

	def get_start_player(self, player=None):
		"""
		common start data
		"""
		# for the game_log here
		res = ["turn~0"]
		res.append("act_width~%f" % self.map.actual_width)
		res.append("aspect~%f" % self.map.aspect)
		res.append("turntime~%d" % self.turntime)
		res.append("loadtime~%d" % self.loadtime)
		res.append("bot_count~%d" % self.bot_count)
		res.append("server_count~%d" % self.server_count)
		# player specific data here
		if player != None:
			res.append("id~%d" % player)
		# map here
		for i, server in enumerate(self.Servers):
			if server.owner == -1:
				res.append("n~%d %s" % (i, server.strify())) # pos[0],pos[1], reserve, invested, limit, owner
			else:
				res.append("s~%d %s" % (i, server.strify())) # pos[0],pos[1], reserve, invested, limit, owner
		if player == None:
			res.append(self.map.show(60))
			res.append("="*20)
		return '\n'.join(res)+'\n'

	def start_turn(self):
		self.turn += 1
		self.orders = [[] for i in range(self.bot_count)] # this is filled by do_moves

	def get_player_update(self, player_id):
		score = "score %d\n" % self.scores[player_id]
		map_lines = 'm ' + '\nm '.join(self.mapdata) + '\n'
		return map_lines + score

	def get_current_state(self):
		"""
		Used only for logging the game-level log
		"""
		res = "bots "
		for i in range(self.bot_count):
			res += "%2d:%s " % (i, str(self.is_alive(i)))
		map_lines = 'm ' + '\nm '.join(self.mapdata) + '\n'
		score_line = "score " + ' '.join( map(str, self.scores) ) + '\n'
		return res+'\n' + map_lines + score_line + '_____\n'

	def parse_move(self, pid, move):
		"""
		parse the given moves-list-of-strings, only check if formatting and data-type is correct
		"""
		orders  = []
		valid   = []
		invalid = []
		for l in move:
			line = l.strip('\r\n').lower()
			# ignore blank lines or comments (Just in case some dumbass wants to debug via the stdout)
			if not line or line[0] == '#':
				continue
			data = line.split()
			if data[0] == 'a':
				# swap
				if len(data[1:]) != VALID_ORDERS['a'][1]:
					invalid.append("%s {invalid formatting, or wrong # of args!}" % line)
				else:
					src_sid, sink_sid, rate = data[1:]
					# validate data-types
					try:
						a_sid = int(src_sid)
						v_sid = int(sink_sid)
						arate = float(rate)
						orders.append( ('a', (a_sid, v_sid, arate)) )
						valid.append(line)
					except:
						invalid.append("%s {Invalid `server_id` or `attack_rate`}" % line)
			elif data[0] == 'w':
				# edit
				if len(data[1:]) != VALID_ORDERS['w'][1]:
					invalid.append("%s {invalid formatting, or wrong # of args!}" % line)
				else:
					src_sid, sink_sid, split_r = data[1:]
					# validate data-types
					try:
						a_sid = int(src_sid)
						v_sid = int(sink_sid)
						split = float(split_r)
						orders.append( ('w', (a_sid, v_sid, split)) )
						valid.append(line)
					except:
						invalid.append("%s {Invalid `server_id`}" % line)
						continue
			else:
				invalid.append("%s {Unknown Action!} [%s]" %(data[0], line))
		
		"""
		Now, we must validate these moves, by calling self.validate_moves()
		"""
		return self.validate_move(pid, orders, valid, invalid)

	def validate_move(self, pid, orders, valid, invalid):
		"""
		Valid move might turn into invalid or ignored ones.
		Check for out of bound map access and other illegal things here:

		* Out-Of-Bounds
		* attack_rate is out-of-range
		* Connection split not a ratio
		* In a set of commands, a victim server is reffered to, twice
		"""
		seen_locations = set() # can't daisy chain locations
		valid_orders   = []
		valid_lines    = []
		ignored        = []		
		for line, order in zip(valid, orders):
			if order[0] in 'awu':
				a_sid, v_sid, _ = order[1]
				# checks on SID below
				if a_sid not in self.Clusters[pid]:
					invalid.append("%s {Can't operate from enemy/neutral (see src_sid)!}" % line)
					continue
				elif v_sid in seen_locations:
					ignored.append("%s {>1 commands with same target-sid! Ignored this.}" % line)
					continue
				elif self.out_of_bounds(v_sid):
					invalid.append("%s {Invalid target-sid!}" % line)
					continue
				else:
					seen_locations.add(order[1][0])
			# checks on ARATE below
			if order[0] == 'a':
				a_sid, v_sid, arate = order[1]
				if v_sid in self.Servers[a_sid].connections.keys() and\
				   self.Servers[a_sid].connections[v_sid].state == STATE_MAP['connected']:
					ignored.append("%s {Already connected to %d from %d. Ignored this.}" % (line, v_sid, a_sid))
					continue
				elif arate < 0 or arate > util.MAX_ARATE:
					invalid.append("%s {Invalid `attack_rate` Acceptable[0, %f]}" % (line, util.MAX_ARATE))
					continue
			if order[0] == 'w':
				a_sid, v_sid, split_r = order[1]
				if split_r > 1.0 or split_r < 0:
					invalid.append("%s {Invalid `connection split` (ratio needed)!}" % line)
					continue
			valid_orders.append(order)
			valid_lines.append(line)
			seen_locations.add(order[1][1])

		return valid_orders, valid_lines, invalid, ignored

	def do_move(self, player_id, moves):
		# parse and validate moves
		orders, valid_lines, invalid_lines, ignored = self.parse_move(player_id, moves)
		# store this guy's orders here. This is reset @ self.start_turn()
		self.orders[player_id] = orders
		return valid_lines, invalid_lines, ignored

	def finish_turn(self):
		# implement valid commands
		for pid, _orders in enumerate(self.orders):
			if _orders:
				for mode, args in _orders:
					if mode == 'a':
						# make a new connection
						if args[0] in self.Servers[args[0]].connections.keys():
							# then this connection must be withdrawing!
							self.Servers[args[0]].connections[args[1]].state = STATE_MAP['making']
						else:
							# make new connection
							self.Servers[args[0]].new_connection(args[1], args[2], self.dist_between(args[0], args[1]))
					elif mode == 'w':
						self.Servers[args[0]].connections[args[1]].state = STATE_MAP['withdrawing']
					elif mode == 'u':
						self.Servers[args[0]].connections[args[1]].arate = args[2]
					# Award scores, or some helper computes for "this player"
			self.scores[pid] += 1
		
		# update connections
		for server in self.Servers:
			# apply regen
			if server.owner != -1:
				server.update_pow(util.DEFAULT_REGEN, 0)
			for v_sid in server.connections.keys():
				conn = server.connections[v_sid]

				# kill dead connections and retract 'withdrawing' ones.
				if conn.state == STATE_MAP['withdrawing']:
					conn.length -= util.DCSPEED
					if conn.length <= 0:
						# delete connection
						server.update_pow(util.DCSPEED + conn.length, -util.DCSPEED - conn.length)
						del server.connections[v_sid]
				
				# apply the damages from 'connected' ones.
				if conn.state == STATE_MAP['connected']:
					server.update_pow(-conn.arate, 0)
					# check if head-on?
					# apply damages ruthlessly, even if it pushes reserve well below zero.
					# That's corrected later on.
					if v_sid in self.Clusters[server.owner]:
						dr = conn.arate
					else:
						dr = -self.amult * conn.arate
					self.Servers[v_sid].update_pow(dr, 0)

				# extend connections in the 'making'
				if conn.state == STATE_MAP['making']:
					if conn.length + util.CSPEED >= conn.full_distance:
						# it connected just before this turn.
						conn.state = STATE_MAP['connected']
						server.update_pow(-conn.full_distance + conn.length, conn.full_distance - conn.length)

						# inflict damage for the right amount of time!
						hit_at = (conn.full_distance - conn.length)/util.CSPEED
						rem_time = 1 - hit_at
						self.Servers[v_sid].update_pow(-self.amult * conn.arate * rem_time, 0)
						conn.length = conn.full_distance
					else:
						# didn't connect even by this turn
						conn.length += util.CSPEED
						server.update_pow(-util.CSPEED, util.CSPEED)
		
		# check for takeovers!
		for attack_server in self.Servers:
			for v_sid in attack_server.connections.keys():
				conn = attack_server.connections[v_sid]
				victim_server = self.Servers[v_sid]
				if victim_server.power <= 0:
					print(attack_server.index, "pawned", v_sid, "of cluster", victim_server.owner)
					self.Clusters[victim_server.owner].remove(v_sid)
					self.Clusters[attack_server.owner].append(v_sid)

					if victim_server.owner == -1:
						victim_server.reserve = victim_server.limit/4.0 + (victim_server.reserve / conn.arate * util.DEFAULT_REGEN)
					else:
						victim_server.reserve = -victim_server.reserve + (victim_server.reserve / conn.arate * util.DEFAULT_REGEN)
					
					victim_server.owner = attack_server.owner

		# update ranks or cutoff level of the game?

	def finish_game(self):
		pass

	def is_alive(self, player):
		# not killed by engine (due to sandbox error or other bot malfunction) AND not dominated by other players
		return not self.killed[player] and self.active[player]

	def kill_player(self, player):
		self.killed[player] = True

	def over(self):
		# if game is decided before max_turns, should return True
		return False

	def get_scores(self, player_id=None):
		if player_id == None:
			return self.scores
		return self.scores[player_id]

	def out_of_bounds(self, sid):
		return sid < 0 or sid >= self.server_count

	def dist_between(self, id1, id2):
		"""
		@brief      Computes (obviously, the shortest) distance between 2 servers(nodes)
		
		@param      self  game-state object
		@param      id1   id of server1
		@param      id2   id of server2
		
		@return     # of routers on the shortest path between the 2 given servers.
		"""
		p1 = self.Servers[id1].pos
		p2 = self.Servers[id2].pos
		return ( ((p1[0]-p2[0])*self.map.actual_width)**2 + ((p1[1]-p2[1])*self.map.actual_width/self.map.aspect)**2 )**0.5

if __name__ == '__main__':
	opts = {"map" : "/home/ananya/gits/saber/maps/test.map",
			"turntime"  : 2,
			"loadtime"  : 2,
			"base_dir"  : "/home/ananya/gits/saber/",
			"cspeed"    : 5.0,
			"dcspeed"   : 10.0,
			"max_arate" : 5.0,
			"regen"     : 0.8,
			"amult"     : 3.2}

	gg = Game(opts)
	gg.start_game()
	print(gg.get_start_player())
	print(gg.get_start_player(1))
	
	gg.start_turn()
	vo, inv, ig = gg.do_move(1, ["a 1 2 0.4000"]) #, "a 0 0 0.1", "a 0 4 0.2", "a 0 2 15", "a 2 0 0.7"])
	print(vo)
	print(inv)
	print(ig)
	gg.finish_turn()
	print(gg.turn)
	print(gg.Servers, gg.Servers[1].connections)

	for i in range(0, 20):
		gg.start_turn()
		vo, inv, ig = gg.do_move(1, [])
		gg.finish_turn()
		print(gg.turn)
		for server in gg.Servers:
			print(server.index, server)
		print(gg.Servers[1].connections)