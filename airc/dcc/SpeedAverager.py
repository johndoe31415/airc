#!/usr/bin/python3
#
#       SpeedAverager - simple object that manages position over time to determine speed
#       Copyright (C) 2017-2022 Johannes Bauer
#
#       This file is part of pycommon.
#
#       pycommon is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; this program is ONLY licensed under
#       version 3 of the License, later versions are explicitly excluded.
#
#       pycommon is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with pycommon; if not, write to the Free Software
#       Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#       Johannes Bauer <JohannesBauer@gmx.de>
#
#       File UUID 02f67c57-2598-484c-bf5c-366b81471e8e

import time

class SpeedAverager():
	def __init__(self, min_secs = 1, average_secs = 25):
		self._min_secs = min_secs
		self._average_secs = average_secs
		self._pos = [ ]

	def add(self, pos):
		now = time.time()
		if (len(self._pos) < 2) or (now > self._pos[-1][0] + self._min_secs):
			self._pos.append((now, pos))

	def _cleanup(self):
		min_time = time.time() - self._average_secs
		while (len(self._pos) > 0) and (self._pos[0][0] < min_time):
			self._pos.pop(0)

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
	import random

	sa = SpeedAverager(min_secs = 0.5)
	pos = 0
	for q in range(250):
		pos += 100 * random.random()
		sa.add(pos)
		print(sa.speed)
		time.sleep(0.1)
	for q in range(250):
		print(sa._pos)
		print(sa.speed)
		time.sleep(0.1)
