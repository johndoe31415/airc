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
from airc.IRCMessageHandler import IRCMessageHandler
from airc.Tools import TextTools

class TextToolTests(unittest.TestCase):
	def setUp(self):
		self._imh = IRCMessageHandler()

	def test_strip_bold_color(self):
		msg = self._imh.parse(b':hakun4!~hakun7@reliant.fritz.box PRIVMSG #mytest :this is \x02bold\x02 and this is \x033color\x03 \x0323other\x03 \x0323,23invisible\x03\r\n')
		self.assertEqual(TextTools.strip_all_control_codes(msg.get_param(1)), "this is bold and this is color other invisible")

	def test_color_1dig_1dig(self):
		msg = self._imh.parse(b':hakun4!~hakun7@reliant.fritz.box PRIVMSG #mytest :\x031,5test\r\n')
		self.assertEqual(TextTools.strip_all_control_codes(msg.get_param(1)), "test")

		# This is a corner case in which implementations differ. As the rest of
		# the shoddy IRC protocol, this is painfully underdefined. Hexchat eats
		# the "0", others mandate that if the first argument is single-digit
		# then all arguments need to be interpreted as single digits (hence
		# leaving the "0" intact). We use the former.
		msg = self._imh.parse(b':hakun4!~hakun7@reliant.fritz.box PRIVMSG #mytest :\x031,50test\r\n')
		self.assertEqual(TextTools.strip_all_control_codes(msg.get_param(1)), "test")

	def test_underlined(self):
		msg = self._imh.parse(b':hakun4!~hakun7@reliant.fritz.box PRIVMSG #mytest :this is \x1funderlined\r\n')
		self.assertEqual(TextTools.strip_all_control_codes(msg.get_param(1)), "this is underlined")

	def test_strikethrough(self):
		msg = self._imh.parse(b':hakun4!~hakun7@reliant.fritz.box PRIVMSG #mytest :this is \x1estriked\r\n')
		self.assertEqual(TextTools.strip_all_control_codes(msg.get_param(1)), "this is striked")

	def test_italics(self):
		msg = self._imh.parse(b':hakun4!~hakun7@reliant.fritz.box PRIVMSG #mytest :this is \x1ditalic\r\n')
		self.assertEqual(TextTools.strip_all_control_codes(msg.get_param(1)), "this is italic")

	def test_reset(self):
		msg = self._imh.parse(b':hakun4!~hakun7@reliant.fritz.box PRIVMSG #mytest :this is \x0freset\r\n')
		self.assertEqual(TextTools.strip_all_control_codes(msg.get_param(1)), "this is reset")
