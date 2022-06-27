#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2020-2022 Johannes Bauer
#
#	This file is part of pyirclib.
#
#	pyirclib is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	pyirclib is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with pyirclib; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

class IRCServer():
	def __init__(self, hostname: str, port: int = 6666, use_ssl: bool = False, password: str | None = None):
		self._hostname = hostname
		self._port = port
		self._password = password
		self._use_ssl = use_ssl

	@property
	def hostname(self):
		return self._hostname

	@property
	def port(self):
		return self._port

	@property
	def use_ssl(self):
		return self._use_ssl

	@property
	def password(self):
		return self._password

	def __str__(self):
		strs = [ f"{self.hostname}:{self.port}" ]
		if self.use_ssl:
			strs.append("SSL")
		if self.password is not None:
			strs.append("PASSWD")
		return "IRCServer<%s>" % (" ".join(strs))
