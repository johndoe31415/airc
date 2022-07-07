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

import unittest
from airc.IRCIdentity import IRCIdentity

class IRCIdentityTests(unittest.TestCase):
	def test_basic_functionality_1(self):
		identity = IRCIdentity(nickname = "foobar")
		self.assertEqual(identity.nickname, "foobar")
		self.assertEqual(identity.username, None)
		self.assertEqual(identity.realname, None)
		self.assertEqual(identity.version, None)
		self.assertEqual(identity.timezone_hrs, None)

	def test_basic_functionality_2(self):
		identity = IRCIdentity(nickname = "foobar", realname = "real", username = "usr", version = "ver", timezone_hrs = 9)
		self.assertEqual(identity.nickname, "foobar")
		self.assertEqual(identity.username, "usr")
		self.assertEqual(identity.realname, "real")
		self.assertEqual(identity.version, "ver")
		self.assertEqual(identity.timezone_hrs, 9)
