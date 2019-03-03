#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2016-2019 Johannes Bauer
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

class Helpers(object):
	@classmethod
	def int_to_ipv4(cls, intip):
		return "%d.%d.%d.%d" % ((intip >> 24) & 0xff, (intip >> 16) & 0xff, (intip >> 8) & 0xff, (intip >> 0) & 0xff)

	@classmethod
	def ipv4_to_int(cls, ip):
		ip = ip.split(".")
		assert(len(ip) == 4)
		assert(all(part.isdigit for part in ip))
		return ((int(ip[0]) & 0xff) << 24) | ((int(ip[1]) & 0xff) << 16) | ((int(ip[2]) & 0xff) << 8) | ((int(ip[3]) & 0xff) << 0)

