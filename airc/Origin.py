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
from airc.Exceptions import InvalidOriginException

class Origin():
	_ORIGIN_REGEX = re.compile(r":((?P<nickname>[^!]+)!(?P<username_is_alias>~?)(?P<username>[^@]+)@)?(?P<hostname>.*)")

	def __init__(self, nickname: str | None, username: str | None, hostname: str, username_is_alias: bool = False):
		self._nickname = nickname
		self._username = username
		self._hostname = hostname
		self._username_is_alias = username_is_alias

	@classmethod
	def parse(cls, text):
		result = cls._ORIGIN_REGEX.fullmatch(text)
		if result is None:
			raise InvalidOriginException(f"Unable to parse origin string: ${text}")
		result = result.groupdict()
		return cls(nickname = result["nickname"], username = result["username"], hostname = result["hostname"], username_is_alias = result["username_is_alias"] is not None)

	@property
	def nickname(self):
		return self._nickname

	@property
	def username(self):
		return self._username

	@property
	def hostname(self):
		return self._hostname

	@property
	def username_is_alias(self):
		return self._username_is_alias

	@property
	def is_server_msg(self):
		return self.nickname is None

	@property
	def is_user_msg(self):
		return self.nickname is not None

	def has_nickname(self, nickname):
		return self.is_user_msg and (nickname.lower() == self.nickname.lower())

	def __str__(self):
		if self.is_server_msg:
			return f"[{self.hostname}]"
		else:
			return f"[{self.nickname}!{'~' if self.username_is_alias else ''}{self.username}@{self.hostname}]"
