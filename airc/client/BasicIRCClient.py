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
import datetime
from airc.Channel import Channel
from airc.ExpectedResponse import ExpectedResponse
from .RawIRCClient import RawIRCClient
from airc.Enums import IRCTimeout, IRCCallbackType, DCCMessageType
from airc.ReplyCode import ReplyCode
from airc.Tools import NameTools, TimeTools
from airc.dcc.DCCRequest import DCCRequestParser
from airc.AsyncBackgroundTasks import AsyncBackgroundTasks

_log = logging.getLogger(__spec__.name)

class BasicIRCClient(RawIRCClient):
	def __init__(self, irc_network, irc_connection):
		super().__init__(irc_network, irc_connection)
		self._bg_tasks = AsyncBackgroundTasks()
		self._bg_tasks.create_task(self._initial_autojoin_channel_coroutine())
		self._channels = { }

	@property
	def channels(self):
		return self._channels.values()

	def get_channel(self, channel_name):
		if channel_name is None:
			return None
		return self._channels.get(channel_name.lower())

	async def _join_channel_loop(self, channel_name):
		channel = Channel(channel_name)
		self._channels[channel_name.lower()] = channel
		while True:
			if not channel.joined:
				finish_conditions = tuple([lambda msg: msg.has_param(0, channel.name, ignore_case = True) and msg.is_cmdcode("JOIN") ])
				try:
					rsp = await asyncio.wait_for(self._irc_connection.tx_message(f"JOIN {channel.name}", expect = ExpectedResponse(finish_conditions = finish_conditions)), timeout = self.config.timeout(IRCTimeout.JoinChannelTimeoutSecs))
					channel.joined = True
				except asyncio.exceptions.TimeoutError:
					delay = self.config.timeout(IRCTimeout.JoinChannelTimeoutSecs)
					_log.error(f"Joining of {channel.name} timed out, waiting for {delay} seconds before retrying.")
					await asyncio.sleep(delay)

			joined_before = channel.joined
			await channel.event()
			if joined_before and (not channel.joined):
				# We were kicked. Delay and retry
				delay = self.config.timeout(IRCTimeout.RejoinChannelTimeSecs)
				_log.info(f"Will rejoin {channel.name} after {delay} seconds.")
				await asyncio.sleep(delay)

	def add_autojoin_channel(self, channel_name):
		self._bg_tasks.create_task(self._join_channel_loop(channel_name))

	async def _initial_autojoin_channel_coroutine(self):
		await self._irc_connection.registration_complete.wait()
		for channel_name in self.irc_network.client_configuration.autojoin_channels:
			self.add_autojoin_channel(channel_name)

	def _handle_ctcp_request(self, nickname, text):
		# If it's already handled internally, return True. Otherwise return
		# False and it will be propagated to the application.
		if (text.lower() == "version") and (self.config.handle_ctcp_version):
			if self.config.version is not None:
				self.ctcp_reply(nickname, f"VERSION {self.config.version}")
			return True
		elif text.lower().startswith("ping") and (self.config.handle_ctcp_ping):
			arg = text[5:]
			if len(arg) == 0:
				self.ctcp_reply(nickname, "PING")
			else:
				self.ctcp_reply(nickname, f"PING {arg}")
			return True
		elif (text.lower() == "time") and (self.config.handle_ctcp_time):
			now = datetime.datetime.utcnow() + datetime.timedelta(0, self.config.time_deviation_secs)
			time_fmt = TimeTools.format_ctcp_timestamp(now)
			self.ctcp_reply(nickname, f"TIME {time_fmt}")
			return True
		elif (text.lower().startswith("dcc")) and (self.config.handle_dcc):
			if self.config.dcc_controller is None:
				_log.error(f"Configured to handle DCC clients, but no DCC controller was registered: Unable to handle {dcc_request}")
				return False

			dcc_request = DCCRequestParser.parse(text)
			if dcc_request.type == DCCMessageType.Send:
				dcc_transfer_handle = self.config.dcc_controller.handle_receive(self, nickname, dcc_request)
				self.fire_callback(IRCCallbackType.DCCTransferStarted, nickname, dcc_transfer_handle)


		return False

	def _handle_ctcp_reply(self, nickname, text):
		# If it's already handled internally, return True. Otherwise return
		# False and it will be propagated to the application.
		pass

	def handle_msg(self, msg):
		super().handle_msg(msg)

		if msg.origin is None:
			return

		if msg.is_cmdcode(ReplyCode.RPL_NAMREPLY):
			channel = self.get_channel(msg.get_param(2))
			if channel is not None:
				nicknames = msg.get_param(3, "").split(" ")
				for nickname in nicknames:
					nickname = NameTools.parse_nickname(nickname)
					channel.add_user(nickname.nickname)
		elif msg.is_cmdcode("JOIN") and msg.origin.is_user_msg:
			channel = self.get_channel(msg.get_param(0))
			if channel is not None:
				channel.add_user(msg.origin.nickname)
		elif msg.is_cmdcode("PART") and msg.origin.is_user_msg:
			channel = self.get_channel(msg.get_param(0))
			if channel is not None:
				channel.remove_user(msg.origin.nickname)
		elif msg.is_cmdcode("QUIT") and msg.origin.is_user_msg:
			for channel in self._channels.values():
				channel.remove_user(msg.origin.nickname)
		elif msg.is_cmdcode("NICK") and msg.origin.is_user_msg:
			for channel in self._channels.values():
				channel.rename_user(msg.origin.nickname, msg.get_param(0))
		elif msg.is_cmdcode("KICK"):
			channel = self.get_channel(msg.get_param(0))
			nickname = msg.get_param(1)
			reason = msg.get_param(2)
			if channel is not None:
				channel.remove_user(nickname)
			if nickname == self.our_nickname:
				_log.warning(f"We were kicked out of {channel.name} by {msg.origin}: {reason}")
				channel.joined = False
		elif msg.is_cmdcode("PRIVMSG") and msg.origin.is_user_msg:
			# We received a private message or channel message
			is_privmsg = not msg.get_param(0).startswith("#")
			text = msg.get_param(1)
			if is_privmsg and (len(text) >= 2) and text.startswith("\x01") and text.endswith("\x01"):
				text = text[1 : -1]
				if not self._handle_ctcp_request(msg.origin.nickname, text):
					self.fire_callback(IRCCallbackType.CTCPRequest, msg.origin.nickname, text)
			elif is_privmsg:
				self.fire_callback(IRCCallbackType.PrivateMessage, msg.origin.nickname, text)
			else:
				channel_name = msg.get_param(0)
				self.fire_callback(IRCCallbackType.ChannelMessage, msg.origin.nickname, channel_name, text)
		elif msg.is_cmdcode("NOTICE") and msg.origin.is_user_msg:
			# We received a notice
			text = msg.get_param(1)
			if (len(text) >= 2) and text.startswith("\x01") and text.endswith("\x01"):
				text = text[1 : -1]
				if not self._handle_ctcp_reply(msg.origin.nickname, text):
					self.fire_callback(IRCCallbackType.CTCPReply, msg.origin.nickname, text)
			else:
				self.fire_callback(IRCCallbackType.Notice, msg.origin.nickname, text)
