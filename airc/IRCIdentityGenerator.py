#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2016-2022 Johannes Bauer
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

from airc.IRCIdentity import IRCIdentity
from airc.Exceptions import OutOfValidNicknamesException

class IRCIdentityGenerator():
	def __iter__(self):
		raise NotImplementedError()

class ListIRCIdentityGenerator():
	def __init__(self, identities: list[IRCIdentity]):
		self._identities = identities

	def __iter__(self):
		yield from self._identities
		raise OutOfValidNicknamesException(f"Exhausted all {len(self._identities)} nicknames, no more left.")
