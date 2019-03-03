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

import math
import time
import random
import threading

class ExponentialBackoff(object):
	def __init__(self, min_time, max_time, backoff_steps = 8, decay_time = 10, randomize_factor = 0):
		self._cnt = 0
		self._steps = backoff_steps - 1
		self._min_time = min_time
		self._max_time = max_time
		self._decay_time = decay_time
		self._randomize_factor = randomize_factor
		self._base = math.exp(math.log(max_time / min_time) / self._steps)
		self._lock = threading.Lock()
		self._timer = None

	@property
	def value(self):
		t = self._min_time * (self._base ** self._cnt)
		t += random.random() * self._randomize_factor * t
		return t

	def _backoff(self):
		with self._lock:
			if self._cnt > 0:
				self._cnt -= 1

	def __call__(self):
		with self._lock:
			t = self.value
			if self._cnt < self._steps:
				self._cnt += 1
			if self._timer is not None:
				self._timer.cancel()
			self._timer = threading.Timer(interval = self._decay_time + 2 * t, function = self._backoff)
			self._timer.start()
		return t

	def sleep(self):
		t = self()
		print("Sleep", t)
		time.sleep(t)
		return t

if __name__ == "__main__":
#	ebo = ExponentialBackoff(5, 120)
#	for i in range(10):
#		print(ebo())
	ebo = ExponentialBackoff(1, 5)
	for i in range(30):
		ebo.sleep()
		time.sleep(1)


