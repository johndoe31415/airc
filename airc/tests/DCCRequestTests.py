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
import ipaddress
from airc.dcc.DCCRequest import DCCRequest

class DCCRequestTests(unittest.TestCase):
	def test_parse_passive(self):
		# This is an actual DCC send request that HexChat 2.16.0 creates; it
		# always issues '199' for the firewalled IP address during passive
		# transfers.
		dccreq = DCCRequest.parse("""DCC SEND "file with space" and quot" 199 0 1 170""")
		self.assertEqual(dccreq.filename, "file with space\" and quot")
		self.assertEqual(dccreq.ip, ipaddress.IPv4Address("0.0.0.199"))
		self.assertEqual(dccreq.port, 0)
		self.assertEqual(dccreq.filesize, 1)
		self.assertEqual(dccreq.passive_token, 170)
		self.assertTrue(dccreq.is_passive)

	def test_parse_active(self):
		# This is an actual DCC send request that HexChat 2.16.0 creates
		dccreq = DCCRequest.parse("""DCC SEND "file with space" 16909060 49439 1""")
		self.assertEqual(dccreq.filename, "file with space")
		self.assertEqual(dccreq.ip, ipaddress.IPv4Address("1.2.3.4"))
		self.assertEqual(dccreq.port, 49439)
		self.assertEqual(dccreq.filesize, 1)
		self.assertEqual(dccreq.passive_token, None)
		self.assertFalse(dccreq.is_passive)
