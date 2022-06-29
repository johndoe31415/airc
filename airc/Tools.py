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

import collections
from airc.Enums import Usermode

class NameTools():
	_Nickname = collections.namedtuple("Nickname", [ "nickname", "mode" ])

	@classmethod
	def parse_nickname(cls, nickname):
		if nickname.startswith("@"):
			nickname = nickname[1:]
			mode = Usermode.Op
		elif nickname.startswith("+"):
			nickname = nickname[1:]
			mode = Usermode.Voice
		else:
			mode = Usermode.Regular
		return cls._Nickname(nickname = nickname, mode = mode)
