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

import time

class AlarmClock(object):
	def __init__(self, timeout):
		self._timeout = timeout
		self._t = time.time()
		self._armed = True

	@property
	def timeout(self):
		return self._t + self._timeout - time.time()

	def settimeout(self, timeout):
		self._timeout = timeout

	def reset(self):
		self._t = time.time()
		self._armed = True

	def __call__(self):
		if self._armed and (time.time() - self._t > self._timeout):
			self._armed = False
			return True
		return False
