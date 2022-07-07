#	airc - Python asynchronous IRC client library with DCC support
#	Copyright (C) 2020-2022 Johannes Bauer
#
#	This file is part of airc.
#
#	airc is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	airc is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with airc; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import asyncio
import logging
import socket
import ssl
import collections
from airc.Enums import IRCTimeout, IRCCallbackType, ConnectionState
from airc.Exceptions import OutOfValidNicknamesException, ServerSeveredConnectionException, ServerMessageParseException
from airc.AsyncBackgroundTasks import AsyncBackgroundTasks
from airc.client import ClientConfiguration
from .IRCServer import IRCServer
from .IRCIdentityGenerator import IRCIdentityGenerator
from .IRCConnection import IRCConnection

_log = logging.getLogger(__spec__.name)

class IRCNetwork():
	def __init__(self, irc_client_class, irc_servers: list[IRCServer], identity_generator: IRCIdentityGenerator, client_configuration: ClientConfiguration | None, identifier = str | None):
		self._bg_tasks = AsyncBackgroundTasks()
		self._irc_client_class = irc_client_class
		self._irc_servers = irc_servers
		self._identity_generator = identity_generator
		self._shutdown = False
		self._connection = None
		self._client_configuration = client_configuration if (client_configuration is not None) else ClientConfiguration()
		self._identifier = identifier
		self._callbacks = collections.defaultdict(list)

	@property
	def connection_state(self):
		if self._connection is None:
			return ConnectionState.Unconnected
		elif not self._connection.registration_complete:
			return ConnectionState.Registering
		else:
			return ConnectionState.Connected

	def get_status(self):
		result = {
			"name":		self.identifier,
			"state":	self.connection_state.value,
		}
		if self._connection is not None:
			result["channels"] = [ channel.get_status() for channel in self._connection.client.channels ]
			result["original_identity"] = self._connection.identity.as_dict() if (self._connection.identity is not None) else None
			result["current_nickname"] = self._connection.client.our_nickname
		return result

	@property
	def irc_client_class(self):
		return self._irc_client_class

	@property
	def connection(self):
		return self._connection

	@property
	def identifier(self):
		return self._identifier

	@property
	def client(self):
		if self.connection is None:
			return None
		return self.connection.client

	@property
	def client_configuration(self):
		return self._client_configuration

	@property
	def identity_generator(self):
		return self._identity_generator

	async def connection_established(self):
		while True:
			if self._connection is not None:
				await self._connection.registration_complete.wait()
				return
			await asyncio.sleep(1)

	def add_listener(self, callback_type: IRCCallbackType, callback):
		self._callbacks[callback_type].append(callback)

	def add_all_listeners(self, callback_object: object):
		for callback_type in IRCCallbackType:
			method_name = "on_" + callback_type.value
			method = getattr(callback_object, method_name, None)
			if method is not None:
				_log.debug("Registering callback method %s for callback type %s", method_name, callback_type)
				self.add_listener(callback_type, method)

	def get_listeners(self, callback_type: IRCCallbackType):
		return iter(self._callbacks.get(callback_type, [ ]))

	async def _connect(self, irc_server):
		_log.info("Connecting to %s", irc_server)
		try:
			writer = None
			(reader, writer) = await asyncio.open_connection(host = irc_server.hostname, port = irc_server.port, ssl = irc_server.tls_ctx)
			self._connection = IRCConnection(self, irc_server, reader, writer)
			await self._connection.start()
		finally:
			if writer is not None:
				writer.close()
			self._connection = None

	async def _connection_loop(self):
		while not self._shutdown:
			for irc_server in self._irc_servers:
				delay = 0
				try:
					await self._connect(irc_server)
				except OutOfValidNicknamesException as e:
					delay = self.client_configuration.timeout(IRCTimeout.ReconnectTimeAfterNicknameExhaustionSecs)
					_log.warning("Delaying reconnect to %s by %d seconds because no nickname was acceptable: %s", irc_server, delay, e)
				except (socket.gaierror, ConnectionRefusedError, ConnectionResetError) as e:
					delay = self.client_configuration.timeout(IRCTimeout.ReconnectTimeAfterConnectionErrorSecs)
					_log.warning("Delaying reconnect to %s by %d seconds because of socket error: %s", irc_server, delay, e)
				except ServerSeveredConnectionException as e:
					delay = self.client_configuration.timeout(IRCTimeout.ReconnectTimeAfterSeveredConnectionSecs)
					_log.warning("Delaying reconnect to %s by %d seconds because server severed the connection: %s", irc_server, delay, e)
				except ServerMessageParseException as e:
					delay = self.client_configuration.timeout(IRCTimeout.ReconnectTimeAfterServerParseExceptionSecs)
					_log.warning("Delaying reconnect to %s by %d seconds because server sent a message we could not parse: %s", irc_server, delay, e)
				except ssl.SSLError as e:
					delay = self.client_configuration.timeout(IRCTimeout.ReconnectTimeAfterTLSErrorSecs)
					_log.warning("Delaying reconnect to %s by %d seconds because we encountered a TLS error: %s", irc_server, delay, e)
				await asyncio.sleep(delay)

	def start(self):
		self._bg_tasks.create_task(self._connection_loop(), "connection_loop")
