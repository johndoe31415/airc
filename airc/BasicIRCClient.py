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

import logging

_log = logging.getLogger(__spec__.name)

class BasicIRCClient():
	def __init__(self, irc_session, irc_connection):
		self._irc_session = irc_session
		self._irc_connection = irc_connection
		self._our_nickname = None

	@property
	def our_nickname(self):
		return self._our_nickname

	@our_nickname.setter
	def our_nickname(self, value):
		_log.info(f"Our nickname with {self._irc_connection.irc_server} is now {value}")
		self._our_nickname = value

	@property
	def irc_session(self):
		return self._irc_session

	@property
	def irc_connection(self):
		return self._irc_connection

	def handle_msg(self, msg):
		if msg.is_cmdcode("ping"):
			data = msg.params[0]
			_log.debug(f"Sending PONG reply to PING request ({data}) on {self._irc_connection.irc_server}.")
			self._irc_connection.tx_message("PONG :%s" % (data))
		elif msg.is_cmdcode("nick") and msg.is_from_user(self.our_nickname):
			# Server changed our nickname
			self.our_nickname = msg.params[0]
