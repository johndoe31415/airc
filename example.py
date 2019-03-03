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
import irc
import logging
from irc.Identity import FakeIdentity

logger = logging.getLogger("irc")

identity = FakeIdentity()
channels = [ "#moo12345" ]
connection = irc.IRCConnection(hostname = "irc.freenode.net", identity = identity, lurk_channel_list = channels, verbose = True, debugging = True)

class ExampleBot(object):
	def __init__(self, connection):
		self._conn = connection

	def privmsg_callback(self, connection, sender, message):
		print("PRIV", sender, message)
		if message == "hey":
			connection.send_msg(sender.nickname, "yeah what?")
		elif message == "scanme":
			connection.send_ctcp(sender.nickname, "VERSION")

	def chanmsg_callback(self, connection, sender, channel, message):
		print("CHAN", sender, channel, message)
		if "i like" in message:
			connection.send_msg(channel, "geeze i totally like that too")

	def ctcpreply_callback(self, connection, sender, reply):
		print("CTCPREPLY", sender, reply)

	def tick(self):
		print(list(self._conn.get_present_people("#moo12345")))

bot = ExampleBot(connection)
connection.append_callback("privmsg", bot.privmsg_callback)
connection.append_callback("chanmsg", bot.chanmsg_callback)
connection.append_callback("ctcpreply", bot.ctcpreply_callback)
while True:
	bot.tick()
	time.sleep(5)
