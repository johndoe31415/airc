#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2020-2020 Johannes Bauer
#
#	This file is part of pyirclib.
#
#	pyirclib is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	pyirclib is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with pyirclib; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

from airc.ExponentialBackoff import ExponentialBackoff

class Channel():
	def __init__(self, name):
		self._name = name
		self._joined = False
		self._banned = False
		self._topic = ""
		self._members = set()
		self._rejoin = ExponentialBackoff(min_time = 10, max_time = 600, randomize_factor = 0.25)

	@property
	def name(self):
		return self._name

	@property
	def joined(self):
		return self._joined

	@joined.setter
	def joined(self, new_value):
		assert(isinstance(new_value, bool))
		self._joined = new_value

	@property
	def banned(self):
		return self._banned

	@banned.setter
	def banned(self, new_value):
		assert(isinstance(new_value, bool))
		self._banned = new_value

	@property
	def topic(self):
		return self._topic

	@topic.setter
	def topic(self, new_value):
		assert(isinstance(new_value, str))
		self._topic = new_value

	@property
	def rejoin(self):
		return self._rejoin

	def joins(self, nickname):
		self._members.add(nickname)

	def parts(self, nickname):
		try:
			self._members.remove(nickname)
		except KeyError:
			pass

	@property
	def members(self):
		return iter(self._members)

	def joinall(self, nicknames):
		for nickname in nicknames:
			self.joins(nickname)

	def change_nick(self, old_nickname, new_nickname):
		if old_nickname in self._members:
			self._members.remove(old_nickname)
			self._members.add(new_nickname)

	def __repr__(self):
		if len(self._members) <= 8:
			return "Chan<%s, %d members: %s>" % (self.name, len(self._members), ", ".join(sorted(self._members)))
		else:
			return "Chan<%s, %d members: %s, ...>" % (self.name, len(self._members), ", ".join(sorted(self._members)[:8]))
