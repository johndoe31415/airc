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
from airc.IRCServer import IRCServer

class IRCServerTests(unittest.TestCase):
	def test_basic_functionality(self):
		srv = IRCServer(hostname = "google.com", port = 80)
		self.assertEqual(srv.hostname, "google.com")
		self.assertEqual(srv.port, 80)

	def test_default_values(self):
		srv = IRCServer(hostname = "freenode.org")
		self.assertEqual(srv.port, 6667)
		self.assertFalse(srv.use_tls)
		self.assertEqual(srv.password, None)

		srv = IRCServer(hostname = "freenode.org", use_tls = True)
		self.assertEqual(srv.port, 6697)
		self.assertTrue(srv.use_tls)

	def test_ssl(self):
		srv = IRCServer(hostname = "freenode.org", use_tls = True)
		self.assertTrue(srv.use_tls)

	def test_password(self):
		srv = IRCServer(hostname = "freenode.org", password = "secret")
		self.assertEqual(srv.password, "secret")
