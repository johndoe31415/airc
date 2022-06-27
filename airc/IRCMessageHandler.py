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

import re
import logging
from airc.ReplyCode import ReplyCode
from airc.Exceptions import ServerMessageParseException

_log = logging.getLogger(__spec__.name)

class IRCMessage():
	def __init__(self, origin, cmdcode, params):
		self._origin = origin
		self._cmdcode = cmdcode
		self._params = params

	@property
	def origin(self):
		return self._origin

	@property
	def cmdcode(self):
		return self._cmdcode

	@property
	def params(self):
		return self._params

	def is_cmdcode(self, cmdcode):
		if isinstance(self.cmdcode, str) and isinstance(cmdcode, str):
			return self.cmdcode.lower() == cmdcode.lower()
		else:
			return self.cmdcode == cmdcode

	def is_from_user(self, username):
		return (self._origin is not None) and (self._origin["nickname"].lower() == username.lower())

	def __str__(self):
		if self.origin is not None:
			if self.origin["nickname"] is not None:
				return "IRCMessage<%s from %s>: %s" % (self.cmdcode, self.origin["nickname"], self.params)
			else:
				return "IRCMessage<%s from host %s>: %s" % (self.cmdcode, self.origin["hostname"], self.params)
		else:
			return "IRCMessage<%s>: %s" % (self.cmdcode, self.params)


class IRCMessageHandler():
	_ORIGIN_REGEX = re.compile(r":((?P<nickname>[^!]+)!(?P<username_is_alias>~?)(?P<username>[^@]+)@)?(?P<hostname>.*)")

	def __init__(self, codec: str = "utf-8"):
		self._codec = codec

	def encode(self, text):
		return (text + "\r\n").encode(self._codec)

	def parse(self, text):
		try:
			msg = text.decode(self._codec).rstrip("\r\n")
			if msg.startswith(":"):
				# Have origin
				(origin, msg) = msg.split(" ", maxsplit = 1)
				result = self._ORIGIN_REGEX.fullmatch(origin)
				if result is None:
					_log.error(f"Could not parse origin string {origin} using regular expression.")
					origin = None
				else:
					origin = result.groupdict()
			else:
				origin = None

			(cmdcode, params) = msg.split(" ", maxsplit = 1)
			if (len(cmdcode) == 3) and (cmdcode.isdigit()):
				cmdcode = int(cmdcode)
				try:
					cmdcode = ReplyCode(cmdcode)
				except ValueError:
					pass

			if params.startswith(":"):
				params = [ params[1:] ]
			elif " :" in params:
				(pre, post) = params.split(" :", maxsplit = 1)
				params = pre.split(" ") + [ post ]
			else:
				params = params.split(" ")
			parsed_msg = IRCMessage(origin = origin, cmdcode = cmdcode, params = params)
			_log.trace(parsed_msg)
			return parsed_msg
		except ValueError as e:
			raise ServerMessageParseException(f"Could not parse server message: {text}") from e
