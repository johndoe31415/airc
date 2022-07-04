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

class DCCConfiguration():
	def __init__(self):
		self._autoaccept = False
		self._autoaccept_download_dir = os.path.expanduser("~/.airc/downloaded/")
		self._download_spooldir = os.path.expanduser("~/.cache/airc/dcc_download/")
		self._enable_passive = False
		self._passive_portrange = None

	@property
	def autoaccept(self):
		return self._autoaccept

	@autoaccept.setter
	def autoaccept(self, value: bool):
		self._autoaccept = value

	@property
	def autoaccept_download_dir(self):
		return self._autoaccept_download_dir

	@autoaccept_download_dir.setter
	def autoaccept_download_dir(self, value: str):
		self._autoaccept_download_dir = value

	@property
	def download_spooldir(self):
		return self._download_spooldir

	@download_spooldir.setter
	def download_spooldir(self, value: str):
		self._download_spooldir = value

	@property
	def download_spooldir_active(self):
		return self.download_spooldir + "/active"

	@property
	def download_spooldir_stale(self):
		return self.download_spooldir + "/stale"

	@property
	def enable_passive(self):
		return self._enable_passive

	@enable_passive.setter
	def enable_passive(self, value: bool):
		self._enable_passive = value

	@property
	def passive_portrange(self):
		return self._passive_portrange

	@passive_portrange.setter
	def passive_portrange(self, value: tuple[int]):
		assert(len(value) == 2)
		assert(value[0] <= value[1])
		self._passive_portrange = value
		self.enable_passive = True
