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

class IRCResponse():
	def __init__(self, finish_cmdcodes: tuple, record_cmdcodes: tuple | None = None):
		self._future = asyncio.Future()
		self._finish_cmdcodes = finish_cmdcodes
		self._record_cmdcodes = record_cmdcodes
		self._messages = [ ]

	@property
	def future(self):
		return self._future

	@property
	def finish_cmdcodes(self):
		return self._finish_cmdcodes

	@property
	def record_cmdcodes(self):
		if self._record_cmdcodes is None:
			return self._finish_cmdcodes
		else:
			return self._record_cmdcodes

	def feed(self, msg):
		do_record = any(msg.is_cmdcode(cmdcode) for cmdcode in self.record_cmdcodes)
		if do_record:
			self._messages.append(msg)

		if self._future.done():
			return False

		is_finished = any(msg.is_cmdcode(cmdcode) for cmdcode in self.finish_cmdcodes)
		if is_finished:
			# This response is done, finalize the future.
			self._future.set_result(self._messages)
			return False
		else:
			# Want more data
			return True
