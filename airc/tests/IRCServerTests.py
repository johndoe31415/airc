#	x509sak - The X.509 Swiss Army Knife white-hat certificate toolkit
#	Copyright (C) 2018-2022 Johannes Bauer
#
#	This file is part of x509sak.
#
#	x509sak is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	x509sak is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with x509sak; if not, write to the Free Software
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
		self.assertEqual(srv.port, 6666)
		self.assertFalse(srv.use_ssl)
		self.assertEqual(srv.password, None)

	def test_ssl(self):
		srv = IRCServer(hostname = "freenode.org", use_ssl = True)
		self.assertTrue(srv.use_ssl)

	def test_password(self):
		srv = IRCServer(hostname = "freenode.org", password = "secret")
		self.assertEqual(srv.password, "secret")
