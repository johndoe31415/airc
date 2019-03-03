#!/usr/bin/python3
#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2016-2019 Johannes Bauer
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

import time
import json
import random
import irc
from irc.Identity import FakeIdentity

identity = FakeIdentity()
channels = [ "#debian" ]
connection = irc.IRCConnection(hostname = "irc.freenode.net", identity = identity, lurk_channel_list = channels, verbose = True, debugging = True)

class CollectBot(object):
	def __init__(self, connection):
		self._conn = connection
		self._versions = { }
		self._asked = set()

	def privmsg_callback(self, connection, sender, message):
		print("PRIV", sender, message)

	def chanmsg_callback(self, connection, sender, channel, message):
		print("CHAN", sender, channel, message)

	def ctcpreply_callback(self, connection, sender, reply):
		print("CTCPREPLY", sender, reply)
		if reply.startswith("VERSION "):
			version = reply[8:]
			nickname = sender.nickname
			print(nickname, version)
			self._versions[nickname] = version
			with open("versions.json", "w") as f:
				json.dump(self._versions, f)

	def tick(self):
		people_not_asked = set(list(self._conn.get_present_people("#debian"))) - self._asked
		if len(people_not_asked) > 0:
			people_not_asked = list(people_not_asked)
			random.shuffle(people_not_asked)
			random_person = people_not_asked.pop()
			print("ASKING", random_person)
			self._asked.add(random_person)
			self._conn.send_ctcp(random_person, "VERSION")

bot = CollectBot(connection)
connection.append_callback("privmsg", bot.privmsg_callback)
connection.append_callback("chanmsg", bot.chanmsg_callback)
connection.append_callback("ctcpreply", bot.ctcpreply_callback)
while True:
	time.sleep(random.randint(60, 90))
	bot.tick()
