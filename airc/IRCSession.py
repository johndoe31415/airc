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
import logging
import socket
import ssl
from .IRCServer import IRCServer
from .IRCIdentityGenerator import IRCIdentityGenerator
from .IRCConnection import IRCConnection
from airc.Enums import IRCSessionVariable
from airc.Exceptions import OutOfValidNicknamesException, ServerSeveredConnectionException, ServerMessageParseException

_log = logging.getLogger(__spec__.name)

class IRCSession():
	def __init__(self, irc_client_class, irc_servers: list[IRCServer], identity_generator: IRCIdentityGenerator):
		self._irc_client_class = irc_client_class
		self._irc_servers = irc_servers
		self._identity_generator = identity_generator
		self._shutdown = False
		self._connection = None
		self._variables = {
			IRCSessionVariable.RegistrationTimeoutSecs:							10,
			IRCSessionVariable.ReconnectTimeAfterNicknameExhaustionSecs:		60,
			IRCSessionVariable.ReconnectTimeAfterConnectionErrorSecs:			5,
			IRCSessionVariable.ReconnectTimeAfterSeveredConnectionSecs:			15,
			IRCSessionVariable.ReconnectTimeAfterServerParseExceptionSecs:		10,
			IRCSessionVariable.ReconnectTimeAfterTLSErrorSecs:					10,
		}

	@property
	def irc_client_class(self):
		return self._irc_client_class

	@property
	def identity_generator(self):
		return self._identity_generator

	def get_var(self, key: IRCSessionVariable):
		return self._variables[key]

	async def _connect(self, irc_server):
		_log.info(f"Connecting to {irc_server}")
		try:
			writer = None
			(reader, writer) = await asyncio.open_connection(host = irc_server.hostname, port = irc_server.port, ssl = irc_server.ssl_ctx)
			connection = IRCConnection(self, irc_server, reader, writer)
			await connection.handle()
		finally:
			if writer is not None:
				writer.close()

	async def _connection_loop(self):
		while not self._shutdown:
			for irc_server in self._irc_servers:
				delay = 0
				try:
					await self._connect(irc_server)
				except OutOfValidNicknamesException as e:
					delay = self.get_var(IRCSessionVariable.ReconnectTimeAfterNicknameExhaustionSecs)
					_log.warning(f"Delaying reconnect to {irc_server} by {delay} seconds because no nickname was acceptable: {e}")
				except (socket.gaierror, ConnectionRefusedError, ConnectionResetError) as e:
					delay = self.get_var(IRCSessionVariable.ReconnectTimeAfterConnectionErrorSecs)
					_log.warning(f"Delaying reconnect to {irc_server} by {delay} seconds because of socket error: {e}")
				except ServerSeveredConnectionException as e:
					delay = self.get_var(IRCSessionVariable.ReconnectTimeAfterSeveredConnectionSecs)
					_log.warning(f"Delaying reconnect to {irc_server} by {delay} seconds because server severed the connection: {e}")
				except ServerMessageParseException as e:
					delay = self.get_var(IRCSessionVariable.ReconnectTimeAfterServerParseExceptionSecs)
					_log.warning(f"Delaying reconnect to {irc_server} by {delay} seconds because server sent a message we could not parse: {e}")
				except ssl.SSLError as e:
					delay = self.get_var(IRCSessionVariable.ReconnectTimeAfterTLSErrorSecs)
					_log.warning(f"Delaying reconnect to {irc_server} by {delay} seconds because we encountered a TLS error: {e}")
				await asyncio.sleep(delay)

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
