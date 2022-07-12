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

import time
import ipaddress
import logging
import aiohttp

_log = logging.getLogger(__spec__.name)

class IPAddressFinder():
	def __init__(self, uri = "https://api.ipify.org/?format=json", cachetime_secs = 15 * 60):
		self._uri = uri
		self._ip = None
		self._cached_timestamp = None
		self._cachetime_secs = cachetime_secs

	@property
	def cache_valid(self):
		now = time.time()
		return (self._cached_timestamp is not None) and (self._ip is not None) and (now - self._cached_timestamp < self._cachetime_secs)

	async def get(self):
		if self.cache_valid:
			return self._ip
		async with aiohttp.ClientSession() as session:
			async with session.get(self._uri) as response:
				response_data = await response.json()
				ip_address = ipaddress.IPv4Address(response_data["ip"])
				self._ip = ip_address
				self._cached_timestamp = time.time()
				_log.info("Determined my own IP address to be %s", ip_address)
				return self._ip
