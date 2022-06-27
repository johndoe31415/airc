#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2020-2022 Johannes Bauer
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

class IRCConnection():
	def __init__(self, irc_session, irc_server, reader, writer):
		self._irc_session = irc_session
		self._irc_server = irc_server
		self._reader = reader
		self._writer = writer
		self._shutdown = False

	def _handle_line(self, line):
		print(line)

	async def handle(self):
		while not self._shutdown:
			line = await self._reader.readline()
			if len(line) == 0:
				# Remote disconnected
				self._shutdown = True
				self._writer.close()
				break
			self._handle_line(line)
