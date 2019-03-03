#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2016-2019 Johannes Bauer
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

import logging
import random
import string
import ssl
import time
import socket
import re
import threading
import collections
from .RXBuffer import RXBuffer
from .ExponentialBackoff import ExponentialBackoff
from .ReplyCode import ReplyCode
from .IRCName import IRCName
from .CallbackRegistry import CallbackRegistry
from .dcc import DCCController
from .TimeoutTimer import TimeoutTimer

class _ServerConnection(object):
	_log = logging.getLogger("irc._ServerConnection")
	def __init__(self, hostname, port, use_ssl, verbose = False):
		self._hostname = hostname
		self._port = port
		self._use_ssl = use_ssl
		self._verbose = verbose
		self._socket = None
		self._buffer = RXBuffer()
		self._connect()

	@property
	def buffer(self):
		return self._buffer

	@property
	def connected(self):
		return ((self._socket is not None) and (self._buffer.connected))

	def _connect(self):
		try:
			self._socket = socket.create_connection((self._hostname, self._port))
		except (socket.gaierror, OSError) as e:
			self._log.error("Error connecting to %s:%d: %s" % (self._hostname, self._port, str(e)))
			return False

		self._log.info("Connected successfully to %s:%d" % (self._hostname, self._port))
		if self._use_ssl:
			self._socket = ssl.wrap_socket(self._socket)
			self._log.debug("SSL wrapper active")
		self._buffer.readfrom(self._socket)
		return True

	def send(self, data):
		assert(isinstance(data, bytes))
		if self._socket is None:
			return
		try:
			self._socket.send(data)
		except (ConnectionResetError, BrokenPipeError) as e:
			self._log.info("Connection reset by %s:%d" % (self._hostname, self._port))
			self.close()

	def recv(self, timeout):
		return self._buffer.get(timeout = timeout)

	def inject(self, data):
		self._buffer.put(data)

	def close(self):
		if self._socket is not None:
			try:
				self._socket.shutdown(socket.SHUT_RDWR)
				self._socket.close()
			except OSError as e:
				pass
		self._buffer.close()
		self._socket = None

class IRCConnection(object):
	_log = logging.getLogger("irc._IRCConnection")
	_RPL_WHOISHOST = re.compile(".*\s(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")

	def __init__(self, hostname, identity, port = 6667, password = None, use_ssl = False, encoding = "utf-8", lurk_channel_list = None, dcc_passive_port_range = None, verbose = False, debugging = False):
		self._log.info("Creating IRC connection to %s:%d as %s", hostname, port, identity)
		self._hostname = hostname
		self._identity = identity
		self._effective_nickname = self._identity.nickname
		self._port = port
		self._password = password
		self._use_ssl = use_ssl
		self._encoding = encoding
		self._rxtxlock = threading.Lock()
		self._verbose = verbose
		self._debugging = debugging
		self._connection = None
		self._my_mode = None
		self._dcc = DCCController(self, passive_port_range = dcc_passive_port_range, debugging = self._debugging)
		self._ping_timer = TimeoutTimer(2 * 60)
		self._timeout_timer = TimeoutTimer(3 * 60)
		self._check_channel_join_timer = TimeoutTimer(300)
		self._check_joined_channels_timer = TimeoutTimer(20 * 60)
		self._whoisreply_channels = set()
		self._backoffs = {
			"reconnect-server":		ExponentialBackoff(5, 300, randomize_factor = 0.1),
			"rejoin-channel":		ExponentialBackoff(45, 400, randomize_factor = 0.4),
		}
		self._callbacks = {
			"privmsg":				[ ],
			"chanmsg":				[ ],
			"ctcpreply":			[ ],
			"incoming-dcc":			[ ],
			"finished-dcc":			[ ],
		}
		self._cbregistry = CallbackRegistry()
		if lurk_channel_list is None:
			self._lurk_channel_list = set()
		else:
			self._lurk_channel_list = set(lurk_channel_list)
		self._joined_channels = set()
		self._present_people = collections.defaultdict(set)
		if not self._verbose:
			self._rxlog = None
		else:
			self._rxlog = open("rxlog_%s.log" % (self._hostname), "a")
		self._connect()
		self._server_thread = threading.Thread(target = self._server_thread_function)
		self._server_thread.start()

	@property
	def dcc_transfers(self):
		return iter(self._dcc)

	@property
	def hostname(self):
		return self._hostname

	def append_callback(self, cbtype, callback):
		self._callbacks[cbtype].append(callback)
		return self

	def _connect(self):
		self._my_mode = None
		self._joined_channels = set()

		self._log.debug("Connecting to %s:%d as %s" % (self._hostname, self._port, self._effective_nickname))
		self._connection = _ServerConnection(self._hostname, self._port, self._use_ssl, verbose = self._verbose)
		if not self._connection.connected:
			return

		if self._password is not None:
			self._log.debug("%s: Sending server password %s", self._hostname, "*" * len(self._password))
			self._txcmd("PASS %s" % (self._password))
		self._txcmd("NICK %s" % (self._effective_nickname))
#		time.sleep(1)
		mode = 8		# Invisible
		self._txcmd("USER %s %d * :%s" % (self._identity.username, mode, self._identity.realname))

	def _txcmd(self, text):
		if self._verbose:
			self._log.debug("-> %s" % (text))
		if not self._connection.connected:
			self._log.error("%s: Cannot transmit '%s' when not connected.", self._hostname, text)
			return
		data = (text + "\r\n").encode(self._encoding)
		with self._rxtxlock:
			try:
				self._connection.send(data)
			except BrokenPipeError as e:
				# Connection broke down
				self._log.error("Lost connection to %s during transmission of command: %s", self._hostname, str(e))
				self._connection.close()


	def inject(self, rawmsg):
		self._connection.inject(rawmsg)

	def _rxcmd(self, timeout):
		if not self._connection.connected:
			return None
		rxdata = self._connection.recv(timeout = timeout)
		if rxdata is not None:
			rxdata = rxdata.decode(self._encoding, errors = "ignore")
			if self._rxlog is not None:
				print(rxdata, file = self._rxlog)
				self._rxlog.flush()
			return rxdata

	def _parse_msg(self, msg):
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

	def _handle_msg(self, msg):
		if len(msg) == 0:
			# Empty message
			return
		self._ping_timer.reset()
		self._timeout_timer.reset()

		if msg[0].startswith(":"):
			# Origin prefix
			origin_prefix = IRCName.parse(msg[0])
			if origin_prefix is None:
				self._log.error("%s: Could not parse origin prefix '%s' of message '%s', rejecting.", self._hostname, msg[0], str(msg))
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
				self._log.warn("%s: No handler '%s' for command %s from %s: \"%s\"", self._hostname, main_handler_name, command, origin_prefix or "server", msg)

	def _handle_numeric_msg(self, origin, numeric_reply_code, args):
		try:
			reply_code = ReplyCode(numeric_reply_code)
		except ValueError:
			self._log.warn("%s: Cannot interpret numeric reply code %d from %s: %s", self._hostname, numeric_reply_code, origin or "server", args)
			return

		if reply_code in [ ReplyCode.ERR_NICKNAMEINUSE, ReplyCode.ERR_ERRONEUSNICKNAME, ReplyCode.ERR_NOTREGISTERED ]:
			# Need to change nickname!
			self._effective_nickname = self._identity.nickname + str(random.randint(0, 99))
			self._log.info("%s: Trying to change my nickname to %s.", self._hostname, self._effective_nickname)
			self._txcmd("NICK %s" % (self._effective_nickname))
		elif reply_code in [ ReplyCode.RPL_WHOISHOST_1, ReplyCode.RPL_WHOISHOST_2 ]:
			if len(args) == 3:
				(forwhom, nickname, message) = args
				if forwhom == nickname:
					result = self._RPL_WHOISHOST.fullmatch(message)
					if result is not None:
						result = result.groupdict()
						ip = result["ip"]
						self._log.info("%s: Learned own IP by RPL_WHOISHOST: %s.", self._hostname, ip)
						self._dcc.set_local_ip(ip)
			else:
				self._log.warn("%s: Got unsupported response in RPL_WHOISHOST: %s", self._hostname, str(args))
		elif reply_code == ReplyCode.ERR_BANNEDFROMCHAN:
			if len(args) == 3:
				(nickname, channel, reason) = args
				self._log.error("%s: Tried to join %s, but we're banned: %s", self._hostname, channel, reason)
			else:
				self._log.error("%s: Tried to join channel but we're banned (%s)", self._hostname, str(args))
		elif reply_code == ReplyCode.RPL_WHOISCHANNELS:
			if len(args) == 3:
				(nickname, username, joined_channels) = args
				if nickname == self._effective_nickname:
					joined_channels = set(channel.lstrip("+@").lower() for channel in joined_channels.split())
					self._whoisreply_channels |= joined_channels
			else:
				self._log.error("%s: Don't know how to interpret %s (%s)", self._hostname, reply_code, str(args))
		elif reply_code == ReplyCode.RPL_ENDOFWHOIS:
			if len(args) == 3:
				(nickname, username, endmsg) = args
				if nickname == self._effective_nickname:
					if self._whoisreply_channels != self._joined_channels:
						self._log.warn("%s: Thought I joined %s but WHOIS says I'm in %s. Updating internal state according to WHOIS.", self._hostname, self._joined_channels, self._whoisreply_channels)
						self._joined_channels = set(self._whoisreply_channels)
					else:
						self._log.debug("%s: WHOIS confirms joined channel list is accurate: %s.", self._hostname, ", ".join(self._joined_channels))
			else:
				self._log.error("%s: Don't know how to interpret %s (%s)", self._hostname, reply_code, str(args))
		elif reply_code == ReplyCode.RPL_NAMREPLY:
			if len(args) == 4:
				channel = args[2]
				names = args[3].split()
				present_people = set(name.lstrip("+@") for name in names)
				for nickname in present_people:
					self._joined_channel(channel, nickname)
			else:
				self._log.error("%s: Don't know how to interpret %s (%s)", self._hostname, reply_code, str(args))

	def _retrieve_local_ip(self):
		self._txcmd("WHOIS %s" % (self._effective_nickname))

	def _handle_server_msg_PING_1(self, server):
		self._txcmd("PONG :%s" % (server))

	def _handle_server_msg_JOIN_1(self, channel):
		self._log.info("%s: Successfully joined channel %s (server message).", self._hostname, channel)
		self._joined_channels.add(channel.lower())

	def _handle_msg_NICK_1(self, origin, new_nickname):
		if origin.nickname == self._effective_nickname:
			self._log.info("%s: My new nickname is %s.", self._hostname, new_nickname)
			self._effective_nickname = new_nickname

	def _handle_msg_JOIN_1(self, origin, channel):
		if origin.nickname == self._effective_nickname:
			self._log.info("%s: Successfully joined channel %s.", self._hostname, channel)
			self._joined_channels.add(channel.lower())
		self._joined_channel(channel, origin.nickname)

	def _handle_msg_INVITE_2(self, origin, target, channel):
		# Just a reply to our PING
		self._log.info("%s: %s invited us to join %s", self._hostname, origin, channel)

	def _handle_msg_PONG_2(self, origin, servername, message):
		# Just a reply to our PING
		pass

	def _handle_msg_MODE_2n(self, origin, channel, modechange, *nicknames):
		# One or more mode changes of users in the channel
		pass

	def _left_channel(self, channel, nickname):
		self._present_people[channel].discard(nickname)

	def _joined_channel(self, channel, nickname):
		if nickname != self._effective_nickname:
			self._present_people[channel].add(nickname)

	def _handle_msg_PART_1(self, origin, channel):
		# Someone left the channel without any message
		self._left_channel(channel, origin.nickname)

	def _handle_msg_PART_2(self, origin, channel, message):
		# Someone left the channel with a message
		self._left_channel(channel, origin.nickname)

	def _handle_msg_TOPIC_2(self, origin, channel, topic):
		# Channel changed topic
		pass

	def _handle_msg_PART_1(self, origin, channel):
		# Someone left the channel
		self._left_channel(channel, origin.nickname)

	def _handle_msg_QUIT_1(self, origin, message):
		# Someone quit IRC, i.e., left all channels
		for namelist in self._present_people.values():
			namelist.discard(origin.nickname)

	def _handle_CTCP_reply(self, origin, reply):
		self.perform_callback("ctcpreply", origin, reply)

	def _handle_msg_NOTICE_2(self, origin, destination, message):
		self._log.debug("%s: Private notice from %s: \"%s\"", self._hostname, origin, message)
		if (len(message) >= 2) and (message[0] == "\x01") and (message[-1] == "\x01"):
			# It's a CTCP reply
			self._handle_CTCP_reply(origin, message[1 : -1])

	def _handle_msg_MODE_2(self, origin, nickname, mode):
		if nickname == self._effective_nickname:
			self._log.info("%s: My mode set to %s.", self._hostname, mode)
			initial_mode_setting = self._my_mode is None
			self._my_mode = mode
			if initial_mode_setting:
				self._retrieve_local_ip()
				self._log.info("%s: Triggering initial joining of all channels.", self._hostname)
				self._join_unjoined_channels()

	def _handle_msg_KICK_3(self, origin, channel, kicked_nick, reason):
		if kicked_nick == self._effective_nickname:
			self._joined_channels.discard(channel.lower())
			rejoin_time = self._backoffs["rejoin-channel"]()
			self._log.info("%s: Was kicked from %s by %s: %s -- will try rejoining in %.1f sec", self._hostname, channel, origin, reason, rejoin_time)
			self._cbregistry.register(("join", channel), rejoin_time, lambda: self.join_channel(channel))

	def _handle_server_msg_NOTICE_2(self, target, message):
		self._log.info("%s: server notice '%s'", self._hostname, message)

	def _handle_server_msg_PRIVMSG_2(self, target, message):
		self._log.info("%s: server private message '%s'", self._hostname, message)

	def _handle_msg_PRIVMSG_2(self, origin, target, message):
		if target.startswith("#"):
			# Channel message
			self.perform_callback("chanmsg", origin, target, message)
		elif target == self._effective_nickname:
			# Private message
			if (len(message) >= 2) and message.startswith("") and message.endswith(""):
				# CTCP message
				message = message[1 : -1]
				self._handle_ctcp_privmsg(origin, target, message)
			else:
				self._log.debug("%s: Private message from %s: \"%s\"", self._hostname, origin, message)
				self.perform_callback("privmsg", origin, message)
		else:
			self._log.warn("%s: Neither channel nor private message? From %s, target %s, message %s", self._hostname, origin, target, message)

	def _handle_ctcp_privmsg(self, origin, target, message):
		msg_lower = message.lower()
		if msg_lower.startswith("dcc "):
			self._dcc.handle(origin, target, message)
		elif msg_lower == "version":
			version = self._identity.version
			if version is not None:
				self._log.debug("%s: Replied CTCP VERSION to %s: %s", self._hostname, origin, version)
				self.send_ctcp(origin.nickname, "VERSION " + version, reply = True)
			else:
				self._log.debug("%s: Ignored CTCP VERSION from %s", self._hostname, origin)
		elif msg_lower == "time":
			now = self._identity.now()
			if now is not None:
				self._log.debug("%s: Replied CTCP TIME to %s: %s", self._hostname, origin, now)
				self.send_ctcp(origin.nickname, "TIME " + now, reply = True)
			else:
				self._log.debug("%s: Ignored CTCP TIME from %s", self._hostname, origin)
		else:
			self._log.warn("%s: Unhandled CTCP message from %s to %s: \"%s\"", self._hostname, origin, target, message)

	def get_present_people(self, channel):
		return iter(self._present_people[channel])

	def perform_callback(self, name, *args):
		for callback in self._callbacks[name]:
			callback(self, *args)

	def join_channel(self, channel):
		if channel not in self._joined_channels:
			self._txcmd("JOIN %s" % (channel))

	def send_msg(self, nickname, message):
		self._txcmd("PRIVMSG %s :%s" % (nickname, message))

	def send_notice(self, nickname, message):
		self._txcmd("NOTICE %s :%s" % (nickname, message))

	def send_ctcp(self, nickname, message, reply = False):
		if not reply:
			self.send_msg(nickname, "" + message + "")
		else:
			self.send_notice(nickname, "" + message + "")

	def _join_unjoined_channels(self):
		if self._my_mode is None:
			# Not yet fully connected, wait.
			return

		unjoined_channels = self._lurk_channel_list - self._joined_channels
		if len(unjoined_channels) == 0:
			return
		for unjoined_channel in unjoined_channels:
			self.join_channel(unjoined_channel)
			time.sleep(1)

	def _check_joined_channels(self):
		self._whoisreply_channels = set()
		self._txcmd("WHOIS %s" % (self._effective_nickname))

	def _server_thread_function(self):
		while True:
			if self._ping_timer.first_timeout:
				self._log.debug("Sensing inactivity on %s, trying to PING server", self._hostname)
				self._txcmd("PING :%s" % (self._effective_nickname))
			elif self._timeout_timer.first_timeout:
				self._log.debug("Connection to %s timed out, trying to reconnect.", self._hostname)
				if self._connection is not None:
					self._connection.close()
				self._connect()
				continue
			elif self._check_channel_join_timer.first_timeout:
				self._check_channel_join_timer.reset()
				self._join_unjoined_channels()
			elif self._check_joined_channels_timer.first_timeout:
				self._check_joined_channels_timer.reset()
				self._check_joined_channels()

			msg = self._rxcmd(timeout = 1.0)
			if msg is not None:
				if self._verbose:
					self._log.debug("<- %s" % (msg))

			# Connection broke down. Retry in some seconds.
			if not self._connection.connected:
				t = self._backoffs["reconnect-server"]()
				self._log.debug("Will try reonnecting to %s:%d in %.0f seconds", self._hostname, self._port, t)
				time.sleep(t)
				self._connect()

			# Check out if callbacks expired
			self._cbregistry.fire()
			self._dcc.time_tick()
			if msg is None:
				continue

			parsed = self._parse_msg(msg)
			if parsed is None:
				continue
			self._handle_msg(parsed)
