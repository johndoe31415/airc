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

class AsyncBackgroundTasks():
	def __init__(self):
		self._tasks = { }
		self._ctr = 0

	def create_task(self, coroutine, name = None):
		if name is None:
			name = f"anonymous-{self._ctr}"
			self._ctr += 1

		assert(name not in self._tasks)
		task = asyncio.create_task(coroutine)
		self._tasks[name] = task
		task.add_done_callback(self._tasks.pop)
		return task
