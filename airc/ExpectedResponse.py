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

class ExpectedResponse():
	def __init__(self, finish_conditions: tuple, record_conditions: tuple | None = None):
		self._future = asyncio.Future()
		self._finish_conditions = finish_conditions
		self._record_conditions = record_conditions
		self._messages = [ ]

	@classmethod
	def on_cmdcode(cls, finish_cmdcodes: tuple, record_cmdcodes: tuple | None = None):
		finish_conditions = tuple(lambda msg, cmdcode = cmdcode: msg.is_cmdcode(cmdcode) for cmdcode in finish_cmdcodes)
		if record_cmdcodes is not None:
			record_conditions = tuple(lambda msg, cmdcode = cmdcode: msg.is_cmdcode(cmdcode) for cmdcode in record_cmdcodes)
		else:
			record_conditions = None
		return cls(finish_conditions = finish_conditions, record_conditions = record_conditions)

	@classmethod
	def on_privmsg_from(cls, nickname: str, ctcp_message: bool = False):
		conditions = [ ]
		conditions.append(lambda msg: msg.is_cmdcode("PRIVMSG"))
		conditions.append(lambda msg: msg.origin.has_nickname(nickname))
		conditions.append(lambda msg: not msg.get_param(0, "").startswith("#"))
		if ctcp_message:
			conditions.append(lambda msg: msg.get_param(1, "").startswith("\x01") and msg.get_param(1, "").endswith("\x01") and len(msg.get_param(1, "")) > 2)
		return cls(finish_conditions = (lambda msg: all(condition(msg) for condition in conditions), ))

	@property
	def future(self):
		return self._future

	@property
	def finish_conditions(self):
		return self._finish_conditions

	@property
	def record_conditions(self):
		if self._record_conditions is None:
			return self._finish_conditions
		else:
			return self._record_conditions

	def feed(self, msg):
		do_record = any(condition(msg) for condition in self.record_conditions)
		if do_record:
			self._messages.append(msg)

		if self._future.done():
			return False

		is_finished = any(condition(msg) for condition in self.finish_conditions)
		if is_finished:
			# This response is done, finalize the future.
			self._future.set_result(self._messages)
			return False
		else:
			# Want more data
			return True
