#	airc - Python asynchronous IRC client library with DCC support
#	Copyright (C) 2016-2022 Johannes Bauer
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

import datetime

class IRCIdentity():
	def __init__(self, nickname: str, username: str | None = None, realname: str | None = None, version: str | None = None, timezone_hrs: int | None = None, clk_deviation_secs: int | None = 0):
		self._nickname = nickname
		self._username = username
		self._realname = realname
		self._version = version
		self._timezone_hrs = timezone_hrs
		self._clk_deviation_secs = clk_deviation_secs

	@property
	def nickname(self):
		return self._nickname

	@property
	def username(self):
		return self._username

	@property
	def realname(self):
		return self._realname

	@property
	def version(self):
		return self._version

	@property
	def timezone_hrs(self):
		return self._timezone_hrs

	def now(self):
		if self.timezone_hrs is not None:
			now = datetime.datetime.utcnow() + datetime.timedelta(0, self._clk_deviation_secs + (3600 * self._timezone_hrs))
			return now.strftime("%a %b %H:%M:%S %Y")
		else:
			return None

	def to_string(self, full = False):
		data = [ self.nickname ]
		if full:
			if self.username is not None:
				data.append(f"user = {self.username}")
			if self.realname is not None:
				data.append(f"real = {self.realname}")
		if self.version is not None:
			data.append(f"IRC client = \"{self.version}\"")
		if self.timezone_hrs is not None:
			data.append(f"TZ {self.timezone_hrs:+d} hrs")
		data = ", ".join(data)
		return f"IRCIdentity<{data}>"

	def __str__(self):
		return self.to_string()
