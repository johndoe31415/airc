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

import enum
import asyncio
from airc.IRCMessageHandler import IRCMessageHandler
from airc.Exceptions import ServerSeveredConnectionException

class IRCConnectionState(enum.IntEnum):
	Established = 0
	Registered = 1

class IRCResponse():
	def __init__(self, finish_cmdcodes: tuple, record_cmdcodes: tuple | None = None):
		self._future = asyncio.Future()
		self._finish_cmdcodes = finish_cmdcodes
		self._record_cmdcodes = record_cmdcodes
		self._messages = [ ]

	@property
	def future(self):
		return self._future

	@property
	def finish_cmdcodes(self):
		return self._finish_cmdcodes

	@property
	def record_cmdcodes(self):
		if self._record_cmdcodes is None:
			return self._finish_cmdcodes
		else:
			return self._record_cmdcodes

	def feed(self, msg):
		do_record = any(msg.is_cmdcode(cmdcode) for cmdcode in self.record_cmdcodes)
		if do_record:
			self._messages.append(msg)

		is_finished = any(msg.is_cmdcode(cmdcode) for cmdcode in self.finish_cmdcodes)
		if is_finished:
			# This response is done, finalize the future.
			self._future.set_result(self._messages)
			return False
		else:
			# Want more data
			return True

class IRCConnection():
	def __init__(self, irc_session, irc_server, reader, writer):
		self._irc_session = irc_session
		self._irc_server = irc_server
		self._reader = reader
		self._writer = writer
		self._shutdown = False
		self._state = None
		self._msghandler = IRCMessageHandler()
		self._client = self._irc_session.irc_client_class(irc_session = self._irc_session, irc_connection = self)
		self._pending_responses = [ ]

	def _rx_message(self, msg):
		if msg.is_cmdcode("error"):
			# Server aborted connection
			raise ServerSeveredConnectionException(msg)
		print(self._pending_responses)
		self._pending_responses = [ response_obj for response_obj in self._pending_responses if response_obj.feed(msg) ]
		self._client.handle_msg(msg)

	def tx_message(self, text: str, response: IRCResponse | None = None):
		print("->", text)
		binmsg = self._msghandler.encode(text)
		self._writer.write(binmsg)
		if response is not None:
			print("HAVE NEW")
			self._pending_responses.append(response)
			return response.future

	async def _handle_rx(self):
		while not self._shutdown:
			line = await self._reader.readline()
			if len(line) == 0:
				# Remote disconnected
				self._shutdown = True
				self._writer.close()
				break
			msg = self._msghandler.parse(line)
			self._rx_message(msg)

	async def _register(self):
		if self._irc_server.password is not None:
			# TODO TEST ME
			rsp = await self.tx_message("PASS %s" % (self._irc_server.password))

		for irc_identity in self._irc_session.identity_generator:
			# Attempt to register under this username
			self.tx_message(f"NICK {irc_identity.nickname}")
			print("RESPONSE NICK")

			mode = "8"
			print("WAITING FOR REGISTRATION TO COMPLETE")
			rsp = await self.tx_message(f"USER {irc_identity.username or irc_identity.nickname} {mode} * :{irc_identity.realname or irc_identity.nickname}", response = IRCResponse(finish_cmdcodes = ("MODE", )))
			print("RESPONSE USER", rsp)
			print("Registration complete.")
			break


	async def handle(self):
		self._state = IRCConnectionState.Established
		rx_task = asyncio.create_task(self._handle_rx())
		await asyncio.gather(self._register(), rx_task)
