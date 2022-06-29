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
import logging
from .BasicIRCClient import BasicIRCClient

_log = logging.getLogger(__spec__.name)

class LurkingIRCClient(BasicIRCClient):
	def __init__(self, irc_session, irc_connection):
		super().__init__(irc_session, irc_connection)
		asyncio.ensure_future(asyncio.create_task(self._lurking_loop()))

	async def _lurking_loop(self):
		await self._irc_connection.registration_complete.wait()
		while True:
			await asyncio.sleep(1)

	def handle_msg(self, msg):
		super().handle_msg(msg)
