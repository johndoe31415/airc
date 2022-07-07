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
import collections
from airc.ReplyCode import ReplyCode
from airc.Enums import IRCCallbackType
from airc.ExpectedResponse import ExpectedResponse
from airc.AsyncBackgroundTasks import AsyncBackgroundTasks

_log = logging.getLogger(__spec__.name)

class RawIRCClient():
	ServerChannel = collections.namedtuple("ServerChannel", [ "name", "user_count", "topic" ])

	def __init__(self, irc_network, irc_connection):
		self._bg_tasks = AsyncBackgroundTasks()
		self._irc_network = irc_network
		self._irc_connection = irc_connection
		self._our_nickname = None
		self.__server_channel_list = None

	@property
	def config(self):
		return self._irc_network.client_configuration

	@property
	def our_nickname(self):
		return self._our_nickname

	@our_nickname.setter
	def our_nickname(self, value):
		_log.info("Our nickname with %s is now %s", self._irc_connection.irc_server, value)
		self._our_nickname = value

	@property
	def irc_network(self):
		return self._irc_network

	@property
	def irc_connection(self):
		return self._irc_connection

	def fire_callback(self, callback_type: IRCCallbackType, *args):
		tasks = [ ]
		for callback in self.irc_network.get_listeners(callback_type):
			tasks.append(self._bg_tasks.create_task(callback(self, *args)))
		return tasks

	def privmsg(self, nickname, text, expect = None):
		return self._irc_connection.tx_message(f"PRIVMSG {nickname} :{text}", expect = expect)

	def notice(self, nickname, text, expect = None):
		return self._irc_connection.tx_message(f"NOTICE {nickname} :{text}", expect = expect)

	def ctcp_request(self, nickname, text, expect = None):
		return self.privmsg(nickname, "\x01" + text + "\x01", expect = expect)

	def ctcp_reply(self, nickname, text, expect = None):
		return self.notice(nickname, "\x01" + text + "\x01", expect = expect)

	async def list_channels(self, cached_result: bool = True):
		if (not cached_result) or (self.__server_channel_list is None):
			expect = ExpectedResponse.on_cmdcode(finish_cmdcodes = (ReplyCode.RPL_LISTEND, ), record_cmdcodes = (ReplyCode.RPL_LIST, ))
			result = await self._irc_connection.tx_message("LIST", expect = expect)
			self.__server_channel_list = [ self.ServerChannel(name = msg.get_param(1), user_count = int(msg.get_param(2, "0")), topic = msg.get_param(3)) for msg in result ]
		return self.__server_channel_list

	def handle_msg(self, msg):
		if msg.is_cmdcode("ping"):
			data = msg.params[0]
			_log.trace("Sending PONG reply to PING request (%s) on %s.", data, self._irc_connection.irc_server)
			self._irc_connection.tx_message(f"PONG :{data}")
		elif msg.is_cmdcode("nick") and msg.origin.has_nickname(self.our_nickname):
			# Server changed our nickname
			self.our_nickname = msg.params[0]
