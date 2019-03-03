#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2016-2019 Johannes Bauer
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

import re
import enum

class IRCNameType(enum.IntEnum):
	SERVER = 1
	NICKNAME = 2
	NICKNAME_HOST = 3

class IRCName(object):
	NICKNAME_HOST_RE = re.compile(":(?P<nickname>[^!]+)!(?P<username>[^@]+)@(?P<hostname>[-0-9a-zA-Z:\.]+)")
	SERVER_RE = re.compile(":(?P<hostname>[-0-9a-zA-Z\.]+)")
	NICKNAME_RE = re.compile(":(?P<nickname>[A-Za-z]+)")

	def __init__(self, nametype, **kwargs):
		self._nametype = nametype
		self._nickname = kwargs.get("nickname")
		self._username = kwargs.get("username")
		self._hostname = kwargs.get("hostname")
		if self._nametype == IRCNameType.SERVER:
			assert(self._hostname is not None)
		elif self._nametype == IRCNameType.NICKNAME:
			assert(self._nickname is not None)
		elif self._nametype == IRCNameType.NICKNAME_HOST:
			assert(self._nickname is not None)
			assert(self._hostname is not None)
			assert(self._username is not None)
		else:
			raise Exception(NotImplemented)

	@property
	def nickname(self):
		return self._nickname

	@property
	def username(self):
		return self._username

	@property
	def hostname(self):
		return self._hostname

	def __eq__(self, other):
		return (self.nickname, self.username, self.hostname) == (other.nickname, other.username, other.hostname)

	def __neq__(self, other):
		return not (self == other)

	@classmethod
	def parse(cls, name):
		for (regex, nametype) in [ (cls.NICKNAME_HOST_RE, IRCNameType.NICKNAME_HOST), (cls.NICKNAME_RE, IRCNameType.NICKNAME), (cls.SERVER_RE, IRCNameType.SERVER) ]:
			result = regex.fullmatch(name)
			if result is not None:
				return cls(nametype, **result.groupdict())

	def __str__(self):
		if self._nametype == IRCNameType.SERVER:
			return "Host<%s>" % (self.hostname)
		elif self._nametype == IRCNameType.NICKNAME:
			return "Nick<%s>" % (self.nickname)
		elif self._nametype == IRCNameType.NICKNAME_HOST:
			return "Nick<%s from %s@%s>" % (self.nickname, self.username, self.hostname)
		else:
			raise Exception(NotImplemented)

if __name__ == "__main__":
	print(IRCName.parse(":foobar"))

