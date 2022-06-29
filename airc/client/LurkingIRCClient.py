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
from airc.Channel import Channel
from airc.IRCResponse import IRCResponse
from .BasicIRCClient import BasicIRCClient
from airc.Enums import IRCSessionVariable
from airc.ReplyCode import ReplyCode

_log = logging.getLogger(__spec__.name)

class LurkingIRCClient(BasicIRCClient):
	def __init__(self, irc_session, irc_connection):
		super().__init__(irc_session, irc_connection)
		asyncio.ensure_future(asyncio.create_task(self._lurking_coroutine()))
		self._channels = { }

	async def _join_channel_loop(self, channel_name):
		channel = Channel(channel_name)
		self._channels[channel_name.lower()] = channel
		while True:
			if not channel.joined:
				finish_conditions = tuple([lambda msg: msg.has_param(0, channel.name, ignore_case = True) and msg.is_cmdcode("JOIN") ])
				try:
					rsp = await asyncio.wait_for(self._irc_connection.tx_message(f"JOIN {channel.name}", response = IRCResponse(finish_conditions = finish_conditions)), timeout = self._irc_session.get_var(IRCSessionVariable.JoinChannelTimeoutSecs))
					channel.joined = True
				except asyncio.exceptions.TimeoutError:
					delay = self._irc_session.get_var(IRCSessionVariable.JoinChannelTimeoutSecs)
					_log.error(f"Joining of {channel.name} timed out, waiting for {delay} seconds before retrying.")
					await asyncio.sleep(delay)
			await asyncio.sleep(1)

	async def _lurking_coroutine(self):
		await self._irc_connection.registration_complete.wait()
		for channel_name in self.irc_session.usr_ctx["lurking_channels"]:
			asyncio.ensure_future(asyncio.create_task(self._join_channel_loop(channel_name)))

	def handle_msg(self, msg):
		super().handle_msg(msg)
		if msg.is_cmdcode(ReplyCode.RPL_NAMREPLY):
			channel = self._channels.get((msg.get_param(2, "")).lower())
			if channel is not None:
				nicknames = msg.get_param(3, "").split(" ")
				for nickname in nicknames:
					channel.add_user(nickname)
