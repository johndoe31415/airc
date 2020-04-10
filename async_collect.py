#!/usr/bin/python3
#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2016-2020 Johannes Bauer
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

import asyncio
import logging
import json
import contextlib
import airc

class DemoIRCHandler():
	def __init__(self):
		self._conn = None
		self._version_filename = "/tmp/irc_version.json"
		self._pending_nicknames = set()
		try:
			with open(self._version_filename) as f:
				self._resolved = json.load(f)
		except FileNotFoundError:
			self._resolved = { }
		self._processed_nicknames = set(self._resolved)
		asyncio.ensure_future(self.resolve_versions())

	async def resolve_versions(self):
		while True:
			await asyncio.sleep(60)
			self._pending_nicknames = (self._pending_nicknames - self._processed_nicknames)
			if (self._conn is not None) and (len(self._pending_nicknames) > 0):
				next_nickname = self._pending_nicknames.pop()
				self._processed_nicknames.add(next_nickname)
				if next_nickname != self._conn.nickname:
					self._conn.send_ctcp(next_nickname, "VERSION")

	async def ctcpreply(self, nickname, reply):
		if reply.lower().startswith("version "):
			version = reply[8:]
			self._resolved[nickname] = version
			with open(self._version_filename, "w") as f:
				json.dump(self._resolved, f)
			print("Have now %d version replies. %d pending." % (len(self._resolved), len(self._pending_nicknames)))

	async def connect(self, connection):
		self._conn = connection

	async def join(self, channel):
		print("joined '%s'" % (channel))
		self._pending_nicknames |= set(channel.members)

	async def enter(self, channel, nickname):
		print("entered '%s': %s" % (channel, nickname))
		self._pending_nicknames.add(nickname)

	async def leave(self, channel, nickname):
		print("left '%s': %s" % (channel, nickname))

	async def chanmsg(self, channel_name, target, message):
		pass
#		print("From %s: %s" % (channel_name, message))
#		await asyncio.sleep(5)
#		self._conn.send_msg(channel_name.nickname, "Yeah got it: %s" % (message))

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("{asctime} {name} [{levelname:.1}]: {message}", style = "{")

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

popular_channels = [ "##linux", "#python", "#archlinux", "#debian", "#freenode", "#kde", "#bash", "#haskell", "#thelounge" ]
popular_channels = [ "#reddit-sysadmin", "#macosx", "#kde-devel", "#cisco", "#monero", "#android", "#chromium", "#kubernetes" ]
async def main():
	handler = DemoIRCHandler()
	ircsessions = [
		#airc.IRCSession(hostname = "irc.freenode.org", port = 6666, handler = handler, channel_list = [ "#qwe1" ], identity = airc.FakeIdentity()),
		airc.IRCSession(hostname = "irc.freenode.org", port = 6666, handler = handler, channel_list = popular_channels, identity = airc.FakeIdentity()),
		#airc.IRCSession(hostname = "127.0.0.1", port = 6666, handler = handler),
		#airc.IRCSession(hostname = "irc.foobar.org", port = 6666, handler = handler),
	]
	tasks = [ ircsession.task() for ircsession in ircsessions ]
	asyncio.gather(*tasks)
	while True:
		await asyncio.sleep(1)

asyncio.run(main())
