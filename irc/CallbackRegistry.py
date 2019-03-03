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

from .AlarmClock import AlarmClock

class Callback(object):
	def __init__(self, timeout, callback_function):
		self._alarmclock = AlarmClock(timeout)
		self._callback_function = callback_function

	@property
	def callback_function(self):
		return self._callback_function

	def expand_time(self, timeout):
		timeout = max(timeout, self._alarmclock.timeout)
		self._alarmclock = AlarmClock(timeout)
		self._callback_function = callback_function

	def fire(self):
		if self._alarmclock():
			return True

class CallbackRegistry(object):
	def __init__(self):
		self._callbacks = { }

	def register(self, key, seconds, callback_function):
		if key not in self._callbacks:
			self._callbacks[key] = Callback(seconds, callback_function)
		else:
			self._callbacks[key].expand_time(seconds, callback_function)

	def fire(self):
		fired_keys = [ ]
		for (key, callback) in self._callbacks.items():
			if callback.fire():
				callback.callback_function()
				fired_keys.append(key)
		for key in fired_keys:
			del self._callbacks[key]

