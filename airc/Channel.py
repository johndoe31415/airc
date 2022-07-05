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

import contextlib
from airc.EventObject import EventObject

class Channel(EventObject):
	def __init__(self, channel_name: str):
		super().__init__()
		self._channel_name = channel_name
		self._joined = False
		self._users = set()

	@property
	def name(self):
		return self._channel_name

	@property
	def joined(self):
		return self._joined

	@property
	def users(self):
		return iter(self._users)

	@joined.setter
	def joined(self, value: bool):
		change = self._joined != value
		self._joined = value
		if change:
			self.signal()

	def add_user(self, nickname: str):
		self._users.add(nickname)

	def remove_user(self, nickname: str):
		with contextlib.suppress(KeyError):
			self._users.remove(nickname)

	def rename_user(self, old_nickname: str, new_nickname: str):
		if old_nickname in self._users:
			self._users.remove(old_nickname)
			self._users.add(new_nickname)

	def __repr__(self):
		if not self.joined:
			return f"Channel<{self.name}, unjoined>"
		elif len(self._users) == 0:
			return f"Channel<{self.name}, no users>"
		else:
			user_str = " ".join(sorted(self.users))
			return f"Channel<{self.name}, {len(self._users)} users: {user_str}>"
