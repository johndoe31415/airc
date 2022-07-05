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
from airc.IRCMessageHandler import IRCMessageHandler
from airc.Exceptions import ServerSeveredConnectionException
from airc.Enums import IRCTimeout
from airc.ExpectedResponse import ExpectedResponse
from airc.ReplyCode import ReplyCode
from airc.AsyncBackgroundTasks import AsyncBackgroundTasks

_log = logging.getLogger(__spec__.name)

class IRCConnection():
	def __init__(self, irc_network, irc_server, reader, writer):
		self._bg_tasks = AsyncBackgroundTasks()
		self._irc_network = irc_network
		self._irc_server = irc_server
		self._reader = reader
		self._writer = writer
		self._shutdown = False
		self._registration_complete = asyncio.Event()
		self._finished = asyncio.Event()
		self._msghandler = IRCMessageHandler()
		self._client = self._irc_network.irc_client_class(irc_network = self._irc_network, irc_connection = self)
		self._pending_responses = [ ]

	@property
	def client(self):
		return self._client

	@property
	def irc_server(self):
		return self._irc_server

	@property
	def registration_complete(self):
		return self._registration_complete

	@property
	def finished(self):
		return self._finished

	def _rx_message(self, msg):
		if msg.is_cmdcode("error"):
			# Server aborted connection
			self._shutdown = True
			_log.error("Server aborted connection with error: %s", msg)
			raise ServerSeveredConnectionException(msg)
		self._pending_responses = [ response_obj for response_obj in self._pending_responses if response_obj.feed(msg) ]
		self._client.handle_msg(msg)

	def tx_message(self, text: str, expect: ExpectedResponse | None = None):
		_log.trace("-> %s : %s", self.irc_server, text)
		binmsg = self._msghandler.encode(text)
		self._writer.write(binmsg)
		if expect is not None:
			self._pending_responses.append(expect)
			return expect.future
		else:
			return None

	async def _handle_rx(self):
		while not self._shutdown:
			line = await self._reader.readline()
			if len(line) == 0:
				# Remote disconnected
				self._shutdown = True
				self._writer.close()
				break
			_log.eavesdrop(f"<- {self.irc_server} : {line}")
			msg = self._msghandler.parse(line)
			self._rx_message(msg)

	async def _register(self):
		if self._irc_server.password is not None:
			rsp = self.tx_message(f"PASS :{self._irc_server.password}")

		for irc_identity in self._irc_network.identity_generator:
			_log.debug("Registering at server %s using identity %s", self._irc_server, irc_identity)

			# Attempt to register under this username
			self.tx_message(f"NICK {irc_identity.nickname}")

			try:
				hostname = "localhost"
				servername = "*"
				rsp = await asyncio.wait_for(self.tx_message(f"USER {irc_identity.username or irc_identity.nickname} {hostname} {servername} :{irc_identity.realname or irc_identity.nickname}", expect = ExpectedResponse.on_cmdcode(finish_cmdcodes = ("MODE", ReplyCode.ERR_NICKNAMEINUSE, ReplyCode.ERR_ERRONEUSNICKNAME, ReplyCode.RPL_ENDOFMOTD, ReplyCode.ERR_NOMOTD))), timeout = self._irc_network.client_configuration.timeout(IRCTimeout.RegistrationTimeoutSecs))
				if rsp[0].is_cmdcode("MODE") or rsp[0].is_cmdcode(ReplyCode.RPL_ENDOFMOTD) or rsp[0].is_cmdcode(ReplyCode.ERR_NOMOTD):
					_log.info("Registeration at server %s using identity %s completed successfully.", self._irc_server, irc_identity)
					self._registration_complete.set()
					self._client.our_nickname = rsp[0].params[0]
					break
				elif rsp[0].is_cmdcode(ReplyCode.ERR_NICKNAMEINUSE):
					_log.warning("Registration at server %s using identity %s did not let us use nickname (already in use).", self._irc_server, irc_identity)
				elif rsp[0].is_cmdcode(ReplyCode.ERR_ERRONEUSNICKNAME):
					_log.warning("Registration at server %s using identity %s did not let us use nickname (erroneous nickname).", self._irc_server, irc_identity)
				continue
			except asyncio.exceptions.TimeoutError:
				# Registration failed. Retry with next identity
				_log.error("Registration at server %s using identity %s timed out after %d seconds.", self._irc_server, irc_identity, self._irc_network.client_configuration.timeout(IRCTimeout.RegistrationTimeoutSecs))

	def start(self):
		rx_task = self._bg_tasks.create_task(self._handle_rx(), "rx_task")
		register_task = self._bg_tasks.create_task(self._register(), "register_task")
		rx_task.add_done_callback(register_task.cancel)
		rx_task.add_done_callback(lambda coro: self._finished.set())
