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

class SpeedAverager(object):
	def __init__(self, min_secs = 1, average_secs = 25):
		self._min_secs = min_secs
		self._average_secs = average_secs
		self._pos = [ ]

	def add(self, pos):
		now = time.time()
		if (len(self._pos) < 2) or (now > self._pos[-1][0] + self._min_secs):
			self._pos.append((time.time(), pos))

	def _cleanup(self):
		min_time = time.time() - self._average_secs
		remove_index = None
		for (index, (t, pos)) in enumerate(self._pos):
			if t < min_time:
				remove_index = index
			else:
				break
		if remove_index is not None:
			self._pos = self._pos[remove_index + 1 : ]

	@property
	def real_speed(self):
		self._cleanup()
		if len(self._pos) == 0:
			return None
		(t0, pos0) = self._pos[0]
		(t1, pos1) = self._pos[-1]
		(tdiff, posdiff) = (t1 - t0, pos1 - pos0)
		if abs(tdiff) < 1e-3:
			return None
		else:
			return posdiff / tdiff

	@property
	def speed(self):
		return self.real_speed or 0

if __name__ == "__main__":
	sa = SpeedAverager()
	for q in range(250):
		sa.add(10 * q)
		print(sa._pos)
		print(sa.speed)
		time.sleep(0.1)
	for q in range(250):
		print(sa._pos)
		print(sa.speed)
		time.sleep(0.1)

