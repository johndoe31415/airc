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

import re
import ipaddress
from airc.Exceptions import DCCRequestParseException

class DCCRequest():
	_DCC_REQUEST_REGEX = re.compile(r"DCC\s+SEND\s+(?P<filename>.+?)\s+(?P<ip>\d+)\s+(?P<port>\d+)\s+(?P<filesize>\d+)(\s+(?P<passive_token>\d+))?", flags = re.IGNORECASE)

	def __init__(self, filename, ip, port, filesize, passive_token):
		self._filename = filename
		self._ip = ip
		self._port = port
		self._filesize = filesize
		self._passive_token = passive_token

	@property
	def filename(self):
		return self._filename

	@property
	def ip(self):
		return self._ip

	@property
	def port(self):
		return self._port

	@property
	def filesize(self):
		return self._filesize

	@property
	def passive_token(self):
		return self._passive_token

	@property
	def is_passive(self):
		return self.port == 0

	@classmethod
	def parse(cls, text):
		result = cls._DCC_REQUEST_REGEX.fullmatch(text)
		if result is None:
			raise DCCRequestParseException(f"Unable to parse DCC SEND request; regex mismatch: {text}")

		result = result.groupdict()
		if result["filename"].startswith("\"") and result["filename"].endswith("\"") and (len(result["filename"]) > 2):
			result["filename"] = result["filename"][1 : -1]

		if result["passive_token"] is None:
			passive_token = None
		else:
			passive_token = int(result["passive_token"])

		port = int(result["port"])
		if (port > 65535) or (port < 0):
			raise DCCRequestParseException(f"Unable to parse DCC SEND request; invalid port: {text}")

		return cls(filename = result["filename"], ip = ipaddress.IPv4Address(int(result["ip"])), port = port, filesize = int(result["filesize"]), passive_token = passive_token)
