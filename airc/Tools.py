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

import collections
import datetime
import asyncio
import re
from airc.Enums import Usermode

class NameTools():
	_Nickname = collections.namedtuple("Nickname", [ "nickname", "mode" ])

	@classmethod
	def parse_nickname(cls, nickname: str):
		if nickname.startswith("@"):
			nickname = nickname[1:]
			mode = Usermode.Op
		elif nickname.startswith("+"):
			nickname = nickname[1:]
			mode = Usermode.Voice
		else:
			mode = Usermode.Regular
		return cls._Nickname(nickname = nickname, mode = mode)

	@classmethod
	def is_channel_name(cls, name: str):
		return (len(name) > 0) and (name[0] in "#&+!")

class TextTools():
	_CONTROL_CODE_REGEX = re.compile("(\x1e|\x1f|\x1d|\x02|\x0f|\x03(\\d{1,2}(,\\d{1,2})?)?)")

	@classmethod
	def strip_all_control_codes(cls, text: str):
		text = cls._CONTROL_CODE_REGEX.sub("", text)
		return text

class TimeTools():
	@classmethod
	def format_ctcp_timestamp(cls, timestamp: datetime.datetime):
		return timestamp.strftime("%a %b %H:%M:%S %Y")

class AsyncTools():
	@classmethod
	async def accept_single_connection_block(cls, host, port, timeout):
		future = asyncio.Future()
		def accept_callback(reader, writer):
			future.set_result((reader, writer))
		server = await asyncio.start_server(accept_callback, host, port, backlog = 1, reuse_address = True, reuse_port = True)
		try:
			(reader, writer) = await asyncio.wait_for(future, timeout = timeout)
			return (reader, writer)
		except asyncio.exceptions.TimeoutError:
			server.close()
			raise

	@classmethod
	async def accept_single_connection(cls, host, port):
		future = asyncio.Future()
		def accept_callback(reader, writer):
			future.set_result((reader, writer))
		server = await asyncio.start_server(accept_callback, host, port, backlog = 1, reuse_address = True, reuse_port = True)
		return (server, future)

class NumberTools():
	@classmethod
	def round_down(cls, value, boundary):
		"""Guaranteed to have at least 'boundary' less bytes (unless the result
		would become zero, then it clips)."""
		value = value - boundary
		if value < 0:
			value = 0
		value = value // boundary
		value = value * boundary
		return value
