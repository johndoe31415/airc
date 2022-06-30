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

class DCCRequest():
	_ACTIVE_DCC_REQUEST_REGEX = re.compile(r"DCC\s+SEND\s+(?P<filename>.+)\s+(?P<ip>\d+)\s+(?P<port>\d+)\s+(?P<filesize>\d+)", flags = re.IGNORECASE)
	_PASSIVE_DCC_REQUEST_REGEX = re.compile(r"DCC\s+SEND\s+(?P<filename>.+)\s+(?P<firewalled_ip>\d+)\s+0\s+(?P<filesize>\d+)\s+(?P<token>\d+)", flags = re.IGNORECASE)

	def __init__(self):
		pass

	@classmethod
	def parse(cls, text):
		result = cls._ACTIVE_DCC_REQUEST_REGEX.fullmatch(text)
		if result is not None:
			pass

		pass
