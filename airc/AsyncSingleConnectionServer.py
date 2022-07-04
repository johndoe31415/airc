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

class AsyncSingleConnectionServer():
	def __init__(self, host: str | None, port: int, close_callback = None):
		self._host = host
		self._port = port
		self._close_callback = close_callback
		self._future = asyncio.Future()
		self._server = None

	@property
	def host(self):
		return self._host

	@property
	def port(self):
		return self._port

	def __accept_callback(self, reader, writer):
		self._future.set_result((reader, writer))

	async def start(self):
		self._server = await asyncio.start_server(self.__accept_callback, self._host, self._port, backlog = 1, reuse_address = True, reuse_port = True)

	def __enter__(self):
		assert(self._server is not None), "server was never started"
		return self

	def __exit__(self, *exception):
		if self._server is not None:
			self._server.close()
		if self._close_callback is not None:
			self._close_callback(self)

	async def __await__(self):
		return await self._future
