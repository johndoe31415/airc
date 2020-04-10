#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2020-2020 Johannes Bauer
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
import socket
import logging
import random
from .ReplyCode import ReplyCode
from .IRCName import IRCName
from .Channel import Channel
from airc import BaseIdentity

class ConnectedIRCSession():
	_log = logging.getLogger("airc.ConnectedIRCSession")

	def __init__(self, session, reader, writer):
		self._session = session
		self._reader = reader
		self._writer = writer
		self._server_read_timeouts = 0
		self._nickname_id = 0
		self._nickname = None
		self._channels = { }
		self._events = { }
		self.perform_callback("connect", self)

	@property
	def nickname(self):
		return self._nickname

	def _event(self, event_name):
		if event_name not in self._events:
			self._events[event_name] = asyncio.Event()
		return self._events[event_name]

	async def _wait_for(self, event_name, timeout_secs):
		try:
			event = self._event(event_name)
			if timeout_secs is not None:
				await asyncio.wait_for(event.wait(), timeout_secs)
			else:
				await event.wait()
			event.clear()
			return True
		except asyncio.TimeoutError:
			return False

	def _signal(self, event_name):
		self._event(event_name).set()

	def channel(self, channel_name):
		assert(channel_name.startswith("#"))
		if channel_name not in self._channels:
			self._channels[channel_name] = Channel(channel_name)
		return self._channels[channel_name]

	def _param(self, name):
		return self._session.get_param(name)

	def _send(self, cmd):
		print("->", cmd)
		self._writer.write((cmd + "\r\n").encode("utf-8"))

	async def _asend(self, cmd):
		await self._writer.write((cmd + "\r\n").encode("utf-8"))

	def _next_nickname(self):
		nickname = self._session.identity.nickname(self._nickname_id)
		self._nickname_id += 1
		return nickname

	def _parse_server_message(self, msg):
		#self._log.debug("PARSE: %s", str(msg))
		split_msg = msg.split()
		args = [ ]
		for (idx, arg) in enumerate(split_msg):
			if (idx > 0) and arg.startswith(":"):
				# Remainder of msg
				args.append(" ".join(split_msg[idx:])[1:])
				break
			args.append(arg)
		return args

	def _handle_server_message(self, msg):
		print("<-", msg)
		if len(msg) == 0:
			# Empty message
			return

		if msg[0].startswith(":"):
			# Origin prefix
			origin_prefix = IRCName.parse(msg[0])
			if origin_prefix is None:
				self._log.error("%s: Could not parse origin prefix '%s' of message '%s', rejecting.", self._session.servername, msg[0], str(msg))
			msg = msg[1:]
		else:
			# Comes directly from server
			origin_prefix = None
			handler_prefix = "_handle_server_msg_"

		if len(msg) == 0:
			# Empty message
			return

		command = msg[0]
		if command.isdigit():
			# Numeric command
			self._handle_numeric_msg(origin_prefix, int(command), msg[1:])
			return
		else:
			if origin_prefix is None:
				handler_prefix = "_handle_server_msg_"
				args = msg[1:]
			else:
				handler_prefix = "_handle_msg_"
				args = [ origin_prefix ] + msg[1:]

			arg_count = len(msg) - 1
			main_handler_name = handler_prefix + command + "_" + str(arg_count)

			handler_names = [ main_handler_name ]
			for i in range(arg_count + 1):
				additional_handler_name = handler_prefix + command + "_" + str(i) + "n"
				handler_names.append(additional_handler_name)

			for handler_name in handler_names:
				handler = getattr(self, handler_name, None)
				if handler is not None:
					handler(*args)
					break
			else:
				self._log.warn("%s: No handler '%s' for command %s from %s: \"%s\"", self._session.servername, main_handler_name, command, origin_prefix or "server", msg)

	def _handle_numeric_msg(self, origin, numeric_reply_code, args):
		try:
			reply_code = ReplyCode(numeric_reply_code)
		except ValueError:
			self._log.warn("%s: Cannot interpret numeric reply code %d from %s: %s", self._session.servername, numeric_reply_code, origin or "server", args)
			return

		if reply_code in [ ReplyCode.ERR_NICKNAMEINUSE, ReplyCode.ERR_ERRONEUSNICKNAME, ReplyCode.ERR_NOTREGISTERED ]:
			# Need to change nickname!
			nickname = self._next_nickname()
			self._log.info("%s: Trying to change my nickname to %s.", self._session.servername, nickname)
			self._send("NICK %s" % (nickname))
		elif reply_code == ReplyCode.RPL_WELCOME:
			# Have a valid nickname assigned
			self._nickname = nickname = args[0]
			self._signal("have_nickname")
		elif reply_code in [ ReplyCode.RPL_WHOISHOST_1, ReplyCode.RPL_WHOISHOST_2 ]:
			if len(args) == 3:
				(forwhom, nickname, message) = args
				if forwhom == nickname:
					result = self._RPL_WHOISHOST.fullmatch(message)
					if result is not None:
						result = result.groupdict()
						ip = result["ip"]
						self._log.info("%s: Learned own IP by RPL_WHOISHOST: %s.", self._session.servername, ip)
						self._dcc.set_local_ip(ip)
			else:
				self._log.warn("%s: Got unsupported response in RPL_WHOISHOST: %s", self._session.servername, str(args))
		elif reply_code == ReplyCode.ERR_BANNEDFROMCHAN:
			if len(args) == 3:
				(nickname, channel, reason) = args
				self._log.error("%s: Tried to join %s, but we're banned: %s", self._session.servername, channel, reason)
			else:
				self._log.error("%s: Tried to join channel but we're banned (%s)", self._session.servername, str(args))
		elif reply_code == ReplyCode.RPL_WHOISCHANNELS:
			if len(args) == 3:
				(nickname, username, joined_channels) = args
				if nickname == self._nickname:
					joined_channels = set(channel.lstrip("+@").lower() for channel in joined_channels.split())
					self._whoisreply_channels |= joined_channels
			else:
				self._log.error("%s: Don't know how to interpret %s (%s)", self._session.servername, reply_code, str(args))
		elif reply_code == ReplyCode.RPL_ENDOFWHOIS:
			if len(args) == 3:
				(nickname, username, endmsg) = args
				if nickname == self._nickname:
					if self._whoisreply_channels != self._joined_channels:
						self._log.warn("%s: Thought I joined %s but WHOIS says I'm in %s. Updating internal state according to WHOIS.", self._session.servername, self._joined_channels, self._whoisreply_channels)
						self._joined_channels = set(self._whoisreply_channels)
					else:
						self._log.debug("%s: WHOIS confirms joined channel list is accurate: %s.", self._session.servername, ", ".join(self._joined_channels))
			else:
				self._log.error("%s: Don't know how to interpret %s (%s)", self._session.servername, reply_code, str(args))
		elif reply_code == ReplyCode.RPL_NAMREPLY:
			# Successfully joined a channel
			if len(args) == 4:
				channel_name = args[2]
				names = args[3].split()
				present_people = set(name.lstrip("+@") for name in names)
				channel = self.channel(channel_name)
				channel.joined = True
				channel.joinall(present_people)
			else:
				self._log.error("%s: Don't know how to interpret %s (%s)", self._session.servername, reply_code, str(args))
		elif reply_code == ReplyCode.RPL_ENDOFNAMES:
			# Execute the "join" callback from this reply code so we already
			# have a list of people in the channel that is fully populated.
			if len(args) == 3:
				channel = self.channel(args[1])
				self.perform_callback("join", channel)

	async def _send_initial_handshake(self):
		if self._session.password is not None:
			self._log.debug("%s: Sending server password %s", self._session.servername, "*" * len(self._session.password))
			self._send("PASS %s" % (self._session.password))
		nickname = self._next_nickname()
		username = self._session.identity.username
		realname = self._session.identity.realname
		self._log.debug("%s: Logging in with nickname '%s'", self._session.servername, nickname)
		self._send("NICK %s" % (nickname))
		mode = 8		# Invisible
		self._send("USER %s %d * :%s" % (username, mode, realname))

	async def _join_channels(self):
		await self._wait_for("have_nickname", timeout_secs = None)

		for channel_name in self._session.channel_list:
			channel = self.channel(channel_name)
			if not channel.joined:
				self._send("JOIN %s" % (channel.name))

	async def _recv_messages(self):
		while not self._reader.at_eof():
			try:
				line = await asyncio.wait_for(self._reader.readline(), timeout = self._param("server_read_timeout_secs"))
			except asyncio.TimeoutError:
				# No response from server in this time
				self._server_read_timeouts += 1
				if self._server_read_timeouts > self._param("server_read_timeout_attempts"):
					break
				else:
					self._send("PING %s" % (self._session.hostname))
				continue
			self._server_read_timeouts = 0
			if len(line) == 0:
				# remote closed connection
				break
			line = line.decode("utf-8", errors = "replace").rstrip("\r\n")
			msg = self._parse_server_message(line)
			self._handle_server_message(msg)
		self._writer.close()

	async def run(self):
		await asyncio.gather(
			self._send_initial_handshake(),
			self._recv_messages(),
			self._join_channels(),
		)

	def _handle_server_msg_PING_1(self, server):
		self._send("PONG :%s" % (server))

#	def _handle_server_msg_JOIN_1(self, channel_name):
#		self._log.info("%s: Successfully joined channel %s (server message).", self._session.servername, channel_name)
#		channel = self.channel(channel_name)
#		channel.joined = True
#		channel.rejoin.cooldown()
#		self.perform_callback("joinmsg", channel)

	def _handle_msg_NICK_1(self, origin, new_nickname):
		if origin.nickname == self._nickname:
			self._log.info("%s: My new nickname is %s.", self._session.servername, new_nickname)
			self._nickname = new_nickname
		for channel in self._channels.values():
			channel.change_nick(origin.nickname, new_nickname)

	def _handle_msg_JOIN_1(self, origin, channel_name):
		channel = self.channel(channel_name)
		channel.joins(origin.nickname)
		if origin.nickname == self._nickname:
			self._log.info("%s: Successfully joined channel %s.", self._session.servername, channel_name)
			channel.joined = True
			channel.rejoin.cooldown()
			self.perform_callback("joinmsg", channel)
		else:
			# Someone else joined this channel
			self.perform_callback("enter", channel, origin.nickname)

	def _handle_msg_INVITE_2(self, origin, target, channel):
		# Just a reply to our PING
		self._log.info("%s: %s invited us to join %s", self._session.servername, origin, channel)

	def _handle_msg_PONG_2(self, origin, servername, message):
		# Just a reply to our PING
		pass

	def _handle_msg_MODE_2n(self, origin, channel, modechange, *nicknames):
		# One or more mode changes of users in the channel
		pass

	def _handle_msg_PART_1(self, origin, channel_name):
		# Someone left the channel without any message
		channel = self.channel(channel_name)
		channel.parts(origin.nickname)
		self.perform_callback("leave", channel, origin.nickname)

	def _handle_msg_PART_2(self, origin, channel_name, message):
		# Someone left the channel with a message
		channel = self.channel(channel_name)
		channel.parts(origin.nickname)
		self.perform_callback("leave", channel, origin.nickname)

	def _handle_msg_TOPIC_2(self, origin, channel, topic):
		# Channel changed topic
		channel = self.channel(channel_name)
		channel.topic = topic

	def _handle_msg_QUIT_1(self, origin, message):
		# Someone quit IRC, i.e., left all channels
		for channel in self._channels.values():
			channel.parts(origin.nickname)

	def _handle_CTCP_reply(self, origin, reply):
		self.perform_callback("ctcpreply", origin.nickname, reply)

	def _handle_msg_NOTICE_2(self, origin, destination, message):
		self._log.debug("%s: Private notice from %s: \"%s\"", self._session.servername, origin, message)
		if (len(message) >= 2) and (message[0] == "\x01") and (message[-1] == "\x01"):
			# It's a CTCP reply
			self._handle_CTCP_reply(origin, message[1 : -1])

	def _handle_msg_MODE_2(self, origin, nickname, mode):
		if nickname == self._nickname:
			self._log.info("%s: My mode set to %s.", self._session.servername, mode)

	async def _rejoin_channel(self, channel_name, delay):
		self._log.info("%s: rejoining channel %s in %.1f seconds", self._session.servername, channel_name, delay)
		await asyncio.sleep(delay)
		self._log.info("%s: attempting rejoining of channel %s", self._session.servername, channel_name)
		self._send("JOIN %s" % (channel_name))

	def _handle_msg_KICK_3(self, origin, channel_name, kicked_nick, reason):
		channel = self.channel(channel_name)
		channel.parts(kicked_nick)
		if kicked_nick == self._nickname:
			channel.joined = False
			asyncio.ensure_future(self._rejoin_channel(channel.name, channel.rejoin.value))
			channel.rejoin.escalate()

	def _handle_server_msg_NOTICE_2(self, target, message):
		self._log.info("%s: server notice '%s'", self._session.servername, message)

	def _handle_server_msg_PRIVMSG_2(self, target, message):
		self._log.info("%s: server private message '%s'", self._session.servername, message)

	def _handle_msg_PRIVMSG_2(self, origin, target, message):
		if target.startswith("#"):
			# Channel message
			self.perform_callback("chanmsg", target, origin.nickname, message)
		elif target == self._nickname:
			# Private message
			if (len(message) >= 2) and message.startswith("\x01") and message.endswith("\x01"):
				# CTCP message
				message = message[1 : -1]
				self._handle_ctcp_privmsg(origin, target, message)
			else:
				self._log.debug("%s: Private message from %s: \"%s\"", self._session.servername, origin, message)
				self.perform_callback("privmsg", origin.nickname, message)
		else:
			self._log.warn("%s: Neither channel nor private message? From %s, target %s, message %s", self._session.servername, origin, target, message)

	def _handle_ctcp_privmsg(self, origin, target, message):
		msg_lower = message.lower()
		if msg_lower.startswith("dcc "):
			self._dcc.handle(origin, target, message)
		elif msg_lower == "version":
			version = self._session.identity.version
			if version is not None:
				self._log.debug("%s: Replied CTCP VERSION to %s: %s", self._session.servername, origin, version)
				self.send_ctcp(origin.nickname, "VERSION " + version, reply = True)
			else:
				self._log.debug("%s: Ignored CTCP VERSION from %s", self._session.servername, origin)
		elif msg_lower == "time":
			now = self._session.identity.now()
			if now is not None:
				self._log.debug("%s: Replied CTCP TIME to %s: %s", self._session.servername, origin, now)
				self.send_ctcp(origin.nickname, "TIME " + now, reply = True)
			else:
				self._log.debug("%s: Ignored CTCP TIME from %s", self._session.servername, origin)
		else:
			self._log.warn("%s: Unhandled CTCP message from %s to %s: \"%s\"", self._session.servername, origin, target, message)

	def get_present_people(self, channel):
		return iter(self._present_people[channel])

	def perform_callback(self, name, *args):
		handler = self._session.handler
		method = getattr(handler, name, None)
		if method is not None:
			asyncio.ensure_future(method(*args))

	def send_msg(self, nickname, message):
		self._send("PRIVMSG %s :%s" % (nickname, message))

	def send_notice(self, nickname, message):
		self._send("NOTICE %s :%s" % (nickname, message))

	def send_ctcp(self, nickname, message, reply = False):
		if not reply:
			self.send_msg(nickname, "\x01" + message + "\x01")
		else:
			self.send_notice(nickname, "\x01" + message + "\x01")

class IRCSession():
	def __init__(self, hostname, handler, port = 6666, password = None, identity = None, channel_list = None):
		self._hostname = hostname
		self._handler = handler
		self._port = port
		self._password = None
		self._identity = identity
		if self._identity is None:
			self._identity = BaseIdentity("user")
		if channel_list is None:
			self._channel_list = tuple()
		else:
			self._channel_list = tuple(channel_list)
		self._defs = {
			"server_read_timeout_attempts":		3,
			"server_read_timeout_secs":			30,
		}

	@property
	def hostname(self):
		return self._hostname

	@property
	def handler(self):
		return self._handler

	@property
	def password(self):
		return self._password

	@property
	def identity(self):
		return self._identity

	@property
	def channel_list(self):
		return self._channel_list

	@property
	def servername(self):
		return "%s:%d" % (self._hostname, self._port)

	def get_param(self, name):
		return self._defs[name]

	async def _handle_connection(self, reader, writer):
		connected_irc_session = ConnectedIRCSession(self, reader, writer)
		await connected_irc_session.run()

	async def _connection_loop(self):
		while True:
			try:
				(reader, writer) = await asyncio.open_connection(host = self._hostname, port = self._port)
				await self._handle_connection(reader, writer)
				writer.close()
			except (ConnectionRefusedError, ConnectionResetError, UnicodeDecodeError, socket.gaierror) as e:
				print(self._hostname, "errored", e)
			print("trying to reconnect...", self._hostname)
			await asyncio.sleep(2)

	async def task(self):
		task = asyncio.create_task(self._connection_loop())
		return task
