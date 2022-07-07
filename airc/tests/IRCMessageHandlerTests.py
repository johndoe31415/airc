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
from airc.IRCMessageHandler import IRCMessageHandler
from airc.ReplyCode import ReplyCode

class IRCMessageHandlerTests(unittest.TestCase):
	def setUp(self):
		self._imh = IRCMessageHandler()

	def test_short(self):
		text = b":blah!~moo@freenode.net PING :foobar\r\n"
		msg = self._imh.parse(text)
		self.assertTrue(msg.is_cmdcode("pInG"))
		self.assertEqual(msg.origin.nickname, "blah")
		self.assertEqual(msg.origin.username, "moo")
		self.assertEqual(msg.origin.hostname, "freenode.net")
		self.assertTrue(msg.origin.has_nickname("bLaH"))
		self.assertTrue(msg.origin.is_user_msg)
		self.assertFalse(msg.origin.is_server_msg)
		self.assertEqual(msg.params, [ "foobar" ])

	def test_bounce(self):
		text = b":*.freenode.net 005 neo ACCEPT=30 AWAYLEN=200 BOT=B CALLERID=g CASEMAPPING=ascii CHANLIMIT=#:20 CHANMODES=IXZbew,k,BEFJLWdfjl,ACDKMNOPQRSTUcimnprstuz CHANNELLEN=64 CHANTYPES=# ELIST=CMNTU ESILENCE=CcdiNnPpTtx EXCEPTS=e :are supported by this server\r\n"
		msg = self._imh.parse(text)
		self.assertTrue(msg.is_cmdcode(ReplyCode.RPL_BOUNCE))
		self.assertEqual(msg.origin.hostname, "*.freenode.net")
		self.assertFalse(msg.origin.is_user_msg)
		self.assertTrue(msg.origin.is_server_msg)
		self.assertEqual(msg.params, [ "neo", "ACCEPT=30", "AWAYLEN=200", "BOT=B", "CALLERID=g", "CASEMAPPING=ascii", "CHANLIMIT=#:20", "CHANMODES=IXZbew,k,BEFJLWdfjl,ACDKMNOPQRSTUcimnprstuz", "CHANNELLEN=64", "CHANTYPES=#", "ELIST=CMNTU", "ESILENCE=CcdiNnPpTtx", "EXCEPTS=e", "are supported by this server" ])

	def test_special_chars(self):
		text = b':MustyHay.eu.ix.Undernet.org 322 x0f495180 #aaaaaaaa 5 :\x02\x030,4 #aaaaaaaa \x02\x030,12 \x8fxxxxxxxxxxxxxxxxxxxxxxxx \x02\x030,4 #aaaaaaaa\r\n'
		msg = self._imh.parse(text)
		self.assertTrue(msg.is_cmdcode(ReplyCode.RPL_LIST))
