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

import os
import logging
import asyncio
import shutil
import contextlib
from airc.dcc.DCCConfiguration import DCCConfiguration
from airc.dcc.DCCRecvTransfer import DCCRecvTransfer
from airc.Exceptions import DCCPassivePortsExhaustedException
from airc.AsyncSingleConnectionServer import AsyncSingleConnectionServer

_log = logging.getLogger(__spec__.name)

class DCCController():
	def __init__(self, dcc_configuration: DCCConfiguration):
		self._config = dcc_configuration
		with contextlib.suppress(FileExistsError):
			os.makedirs(self.config.download_spooldir_stale)
		with contextlib.suppress(FileExistsError):
			os.makedirs(self.config.download_spooldir_active)
		if self.config.listening_portrange is None:
			self._passive_ports = [ ]
		else:
			self._passive_ports = list(range(self.config.listening_portrange[0], self.config.listening_portrange[1] + 1))
		self._cleanup_spooldir()

	@property
	def config(self):
		return self._config

	def _listdirs(self, *dirnames):
		for dirname in dirnames:
			for filename in os.listdir(dirname):
				full_filename = dirname + "/" + filename
				yield full_filename

	def _cleanup_spooldir(self):
		if not self.config.cleanup_spooldir_on_startup:
			return

		# Remove spooldir entries less than discard_tail_at_resume bytes in
		# size (these would be discarded anyways, not resumed)
		for filename in self._listdirs(self.config.download_spooldir_stale, self.config.download_spooldir_active):
			if os.stat(filename).st_size < self.config.discard_tail_at_resume:
				os.unlink(filename)

		for filename in self._listdirs(self.config.download_spooldir_active):
			migrated_filename = self.config.download_spooldir_stale + "/" + os.path.basename(filename)
			if not os.path.exists(migrated_filename):
				shutil.move(filename, migrated_filename)
			else:
				_log.warning(f"Wanted to move active spoolfile {filename} to stale directory as {migrated_filename}, but the latter already exist. Refusing to overwrite/migrate.")

	async def allocate_passive_port(self):
		def _close_callback(server):
			_log.debug(f"Port reclaimed: {server.port}")
			self._passive_ports.append(server.port)

		for _ in range(len(self._passive_ports)):
			try:
				passive_port = self._passive_ports.pop(0)
				single_connection_server = AsyncSingleConnectionServer(host = None, port = passive_port, close_callback = _close_callback)
				await single_connection_server.start()
				break
			finally:
				self._passive_ports.append(passive_port)
		else:
			raise DCCPassivePortsExhaustedException(f"Passive DCC transfer requested in {dcc_request}, but all passive ports exhausted. Cannot transfer.")
		return single_connection_server

	def handle_receive(self, irc_client, nickname, dcc_request):
		dcc_transfer = DCCRecvTransfer(self, irc_client, nickname, dcc_request)
		asyncio.ensure_future(dcc_transfer.handle())
		return dcc_transfer
