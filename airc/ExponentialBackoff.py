#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2016-2020 Johannes Bauer
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

import math
import time
import random
import asyncio

class ExponentialBackoff(object):
	def __init__(self, min_time, max_time, level_count = 8, randomize_factor = 0):
		self._min_time = min_time
		self._max_time = max_time
		self._level_count = level_count
		self._randomize_factor = randomize_factor

		self._current_level = 0
		self._base = math.exp(math.log(max_time / min_time) / (self._level_count - 1))
		self._last_cooldown = 0

	def cooldown(self):
		if self._last_cooldown is None:
			return
		if self._current_level == 0:
			return
		time_since_last_cooldown = time.time() - self._last_cooldown
		if time_since_last_cooldown > self._max_time:
			self._current_level -= 1
			self._last_cooldown = time.time()

	def escalate(self):
		if self._current_level < self._level_count - 1:
			self._current_level += 1

	def _time_at_level(self, level):
		t = self._min_time * (self._base ** level)
		return t

	@property
	def value(self):
		t = self._time_at_level(self._current_level)
		t += random.random() * self._randomize_factor * t
		return t

	def sleep(self):
		t = self.value
		time.sleep(t)
		return t

	async def asleep(self):
		t = self.value
		await asyncio.sleep(t)
		return t

if __name__ == "__main__":
	class RLimit():
		def __init__(self, secs):
			self._secs = secs
			self._last = None

		def msg(self):
			if self._last is not None:
				time_passed = time.time() - self._last
				if time_passed < self._secs:
					print("Reject %f" % (time_passed))
					return False
			print("Accept")
			self._last = time.time()
			return True


	rlimit = RLimit(0.5)
	ebo = ExponentialBackoff(0.1, 2, randomize_factor = 0.5)
	for i in range(30):
		if rlimit.msg():
			ebo.cooldown()
		else:
			ebo.escalate()
		print(ebo.sleep())
