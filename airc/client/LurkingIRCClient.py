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
from airc.Enums import IRCSessionVariable, IRCCallbackType
from airc.ReplyCode import ReplyCode
from airc.Tools import NameTools

_log = logging.getLogger(__spec__.name)

class LurkingIRCClient(BasicIRCClient):
	def __init__(self, irc_session, irc_connection):
		super().__init__(irc_session, irc_connection)
		asyncio.ensure_future(asyncio.create_task(self._lurking_coroutine()))
		self._channels = { }

	@property
	def channels(self):
		return self._channels

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

			joined_before = channel.joined
			await channel.event()
			if joined_before and (not channel.joined):
				# We were kicked. Delay and retry
				delay = self._irc_session.get_var(IRCSessionVariable.RejoinChannelTimeSecs)
				_log.info(f"Will rejoin {channel.name} after {delay} seconds.")
				await asyncio.sleep(delay)

	async def _lurking_coroutine(self):
		await self._irc_connection.registration_complete.wait()
		for channel_name in self.irc_session.usr_ctx["lurking_channels"]:
			asyncio.ensure_future(asyncio.create_task(self._join_channel_loop(channel_name)))

	def _get_channel(self, channel_name):
		if channel_name is None:
			return None
		return self._channels.get(channel_name.lower())

	def _handle_ctcp_request(self, nickname, text):
		# If it's already handled internally, return True. Otherwise return
		# False and it will be propagated to the application.
		return False

	def handle_msg(self, msg):
		super().handle_msg(msg)

		if msg.origin is None:
			return

		if msg.is_cmdcode(ReplyCode.RPL_NAMREPLY):
			channel = self._get_channel(msg.get_param(2))
			if channel is not None:
				nicknames = msg.get_param(3, "").split(" ")
				for nickname in nicknames:
					nickname = NameTools.parse_nickname(nickname)
					channel.add_user(nickname.nickname)
		elif msg.is_cmdcode("JOIN") and msg.origin.is_user_msg:
			channel = self._get_channel(msg.get_param(0))
			if channel is not None:
				channel.add_user(msg.origin.nickname)
		elif msg.is_cmdcode("PART") and msg.origin.is_user_msg:
			channel = self._get_channel(msg.get_param(0))
			if channel is not None:
				channel.remove_user(msg.origin.nickname)
		elif msg.is_cmdcode("NICK") and msg.origin.is_user_msg:
			for channel in self._channels.values():
				channel.rename_user(msg.origin.nickname, msg.get_param(0))
		elif msg.is_cmdcode("KICK"):
			channel = self._get_channel(msg.get_param(0))
			nickname = msg.get_param(1)
			reason = msg.get_param(2)
			if channel is not None:
				channel.remove_user(nickname)
			if nickname == self.our_nickname:
				_log.warning(f"We were kicked out of {channel.name} by {msg.origin}: {reason}")
				channel.joined = False
		elif msg.is_cmdcode("PRIVMSG") and msg.origin.is_user_msg:
			# We received a private message
			text = msg.get_param(1)
			if (len(text) >= 2) and text.startswith("\x01") and text.endswith("\x01"):
				text = text[1 : -1]
				if self._handle_ctcp_request(msg.origin.nickname, text):
					self.fire_callback(IRCCallbackType.CTCPRequest, msg.origin.nickname, text)
			else:
				self.fire_callback(IRCCallbackType.PrivateMessage, msg.origin.nickname, text)
