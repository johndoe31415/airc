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

class TimeoutTimer(object):
	def __init__(self, timeout_secs):
		self._t = time.time()
		self._timeout_secs = timeout_secs
		self._cnt = 0

	@property
	def time_since_reset(self):
		now = time.time()
		return now - self._t

	@property
	def timed_out(self):
		return self.time_since_reset > self._timeout_secs

	@property
	def timeout_count(self):
		if self.timed_out:
			self._cnt += 1
		return self._cnt

	@property
	def first_timeout(self):
		return self.timeout_count == 1

	def reset(self):
		self._cnt = 0
		self._t = time.time()
