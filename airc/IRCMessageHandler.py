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

import logging
from airc.ReplyCode import ReplyCode
from airc.Origin import Origin
from airc.Exceptions import ServerMessageParseException, InvalidOriginException

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

	def get_param(self, param_index, default_value = None):
		if param_index >= len(self._params):
			return default_value
		return self._params[param_index]

	def has_param(self, param_index, value, ignore_case = False):
		param_value = self.get_param(param_index)
		if param_value is None:
			return False
		if ignore_case:
			param_value = param_value.lower()
			value = value.lower()
		return param_value == value

	def __str__(self):
		if self.origin is not None:
			return f"IRCMessage<{self.cmdcode} from {self.origin}>: {self.params}"
		else:
			return f"IRCMessage<{self.cmdcode}>: {self.params}"

class IRCMessageHandler():
	def __init__(self, codec: str = "utf-8"):
		self._codec = codec

	def encode(self, text):
		return (text + "\r\n").encode(self._codec)

	def parse(self, text):
		try:
			msg = text.decode(self._codec, errors = "replace").rstrip("\r\n")
			if msg.startswith(":"):
				# Have origin
				(origin_text, msg) = msg.split(" ", maxsplit = 1)
				try:
					origin = Origin.parse(origin_text)
				except InvalidOriginException as e:
					_log.error("Could not parse origin string %s using regular expression: %s", origin_text, e)
					origin = Origin(hostname = origin_text, nickname = None, username = None)
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
		except (ValueError, UnicodeDecodeError) as e:
			raise ServerMessageParseException(f"Could not parse server message: {text}") from e
