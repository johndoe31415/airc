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
		if isinstance(self.cmdcode, str):
			return self.cmdcode.lower() == cmdcode.lower()
		else:
			return self.cmdcode == cmdcode

	def __str__(self):
		if self.origin is not None:
			return "IRCMessage<%s from %s>: %s" % (self.cmdcode, self.origin, self.params)
		else:
			return "IRCMessage<%s>: %s" % (self.cmdcode, self.params)


class IRCMessageHandler():
	_LONG_ARG_SEPARATOR = re.compile(r" ?:")

	def __init__(self, codec: str = "utf-8"):
		self._codec = codec

	def encode(self, text):
		return (text + "\r\n").encode(self._codec)

	def parse(self, msg):
		msg = msg.decode(self._codec).rstrip("\r\n")
		if msg.startswith(":"):
			# Have origin
			(origin, msg) = msg.split(" ", maxsplit = 1)
		else:
			origin = None

		(cmdcode, params) = msg.split(" ", maxsplit = 1)
		if (len(cmdcode) == 3) and (cmdcode.isdigit()):
			cmdcode = int(cmdcode)
			try:
				cmdcode = ReplyCode(cmdcode)
			except ValueError:
				pass

		if ":" in params:
			(pre, post) = self._LONG_ARG_SEPARATOR.split(params, maxsplit = 1)
			if len(pre) == 0:
				params = [ post ]
			else:
				params = pre.split(" ") + [ post ]
		else:
			params = params.split(" ")
		parsed_msg = IRCMessage(origin = origin, cmdcode = cmdcode, params = params)
		_log.trace(parsed_msg)
		return parsed_msg
