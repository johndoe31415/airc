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

import asyncio
from .SpeedAverager import SpeedAverager

class SpeedThrottler():
	def __init__(self, chunk_size: int, target: float | None = None):
		self._target = target
		self._chunk_size = chunk_size
		self._current_speed = SpeedAverager(min_secs = 0.1, average_secs = 5)
		self._bytes_total = 0
		self._correction_factor = 1.0
		percent_per_megabyte = 1
		self._adjustment_factor = chunk_size / ((1 / (percent_per_megabyte / 100)) * 1024 * 1024)

	@property
	def target(self):
		return self._target

	@target.setter
	def target(self, value: float | None):
		self._target = value
		self._bytes_total = 0

	async def throttle(self, bytes_read: int):
		if self._target is None:
			# No throttling requested
			return

		self._bytes_total += bytes_read
		self._current_speed.add(self._bytes_total)
		speed = self._current_speed.real_speed
		if speed is not None:
			#print(f"{round(speed):8d} {self._correction_factor}")
			if speed < self._target * 0.95:
				# We're too slow, decrease delay
				self._correction_factor *= (1 - self._adjustment_factor)
			elif speed > self._target * 1.05:
				# We're too fast, increase delay
				self._correction_factor *= (1 + self._adjustment_factor)
			if self._correction_factor < 0.1:
				self._correction_factor = 0.1
			elif self._correction_factor > 10:
				self._correction_factor = 10

		target_delay = self._correction_factor * (self._chunk_size / self._target)
		if target_delay >= 0.001:
			await asyncio.sleep(target_delay)

if __name__ == "__main__":
	async def handler(reader, writer):
		print("Connected:", reader, writer)
		#dd if=/dev/zero bs=1M count=1000 | socat - tcp-connect:127.0.0.1:1234
		chunk_size = 128 * 1024
		throttler = SpeedThrottler(chunk_size, 1234 * 1000)
		while True:
			data = await reader.read(chunk_size)
			await throttler.throttle(len(data))
			if len(data) == 0:
				break
		print("Disconnected.")

	async def main():
		async with await asyncio.start_server(handler, "0.0.0.0", 1234, reuse_port = True) as server:
			await server.serve_forever()
	asyncio.run(main())
