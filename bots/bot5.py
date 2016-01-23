#!/usr/bin/env python

from Quantum import *
# any other imports here

class myBot():
	"""
	valid BOT
	"""
	def __init__(self):
		self.name = "valid Bot"
		# initialise any persistent data structures (if needed)
	
	def do_setup(self, game):
		self.gs = game
		print(game.my_nodes)
		print(game.neutrals)
		print(game.enemy_nodes)
		self.closest = self.get_closest_nodes(game.my_nodes[0])

	def do_turn(self, game):
		print(game.turn)
		if game.turn == 1:
			game.attack(1, 0.4)
		elif game.turn == 999:
			pass		

	def get_closest_nodes(self, src_index):
		sid_dist = []
		for sid in self.gs.neutrals + self.gs.enemy_nodes:
			sid_dist.append((self.gs.dist_between(src_index, sid), sid))
		return sorted(sid_dist, key=lambda dist: dist[0])

if __name__ == '__main__':
	try:
		ServerStack.launch(myBot())
	except KeyboardInterrupt:
		print("Ctrl-C, bye!")