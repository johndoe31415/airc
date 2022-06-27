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

from airc.ReplyCode import ReplyCode

class IRCMessage():
	def __init__(self, prefix, cmdcode, params):
		self._prefix = prefix
		self._cmdcode = cmdcode
		self._params = params

	@property
	def prefix(self):
		return self._prefix

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
		if self.prefix is not None:
			return "IRCMessage<%s from %s>: %s" % (self.cmdcode, self.prefix, self.params)
		else:
			return "IRCMessage<%s>: %s" % (self.cmdcode, self.params)


class IRCMessageHandler():
	def __init__(self, codec: str = "utf-8"):
		self._codec = codec

	def encode(self, text):
		return (text + "\r\n").encode(self._codec)

	def parse(self, msg):
		msg = msg.decode(self._codec).rstrip("\r\n")
		if msg.startswith(":"):
			# Have prefix
			(prefix, msg) = msg.split(" ", maxsplit = 1)
		else:
			prefix = None

		(cmdcode, params) = msg.split(" ", maxsplit = 1)
		if (len(cmdcode) == 3) and (cmdcode.isdigit()):
			cmdcode = int(cmdcode)
			try:
				cmdcode = ReplyCode(cmdcode)
			except ValueError:
				pass

		if ":" in params:
			if params[0] == ":":
				params = [ params[1:] ]
			else:
				(pre, post) = params.split(":", maxsplit = 1)
				params = pre.split(" ") + [ post ]
		else:
			params = params.split(" ")
		return IRCMessage(prefix = prefix, cmdcode = cmdcode, params = params)
