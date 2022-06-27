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

import asyncio
from .IRCServer import IRCServer
from .IRCIdentityGenerator import IRCIdentityGenerator
from .IRCConnection import IRCConnection

class IRCSession():
	def __init__(self, irc_servers: list[IRCServer], identity_generator: IRCIdentityGenerator):
		self._irc_servers = irc_servers
		self._identity_generator = identity_generator
		self._shutdown = False
		self._connection = None

	@property
	def identity_generator(self):
		return self._identity_generator

	async def _connect(self, irc_server):
		try:
			writer = None
			(reader, writer) = await asyncio.open_connection(host = irc_server.hostname, port = irc_server.port)
			connection = IRCConnection(self, irc_server, reader, writer)
			await connection.handle()
		finally:
			if writer is not None:
				writer.close()

	async def _connection_loop(self):
		while not self._shutdown:
			for irc_server in self._irc_servers:
				await self._connect(irc_server)

#			try:
#				(reader, writer) = await asyncio.open_connection(host = self._hostname, port = self._port)
#				await self._handle_connection(reader, writer)
#				writer.close()
#			except (ConnectionRefusedError, ConnectionResetError, UnicodeDecodeError, socket.gaierror) as e:
#				print(self._hostname, "errored", e)
#			print("trying to reconnect...", self._hostname)
#			await asyncio.sleep(2)

	def task(self):
		task = asyncio.create_task(self._connection_loop())
		return task
