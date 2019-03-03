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

import queue
import logging
import threading

class _ReadingWorkerThread(threading.Thread):
	_log = logging.getLogger("irc._ReadingWorkerThread")

	def __init__(self, socket, callback):
		threading.Thread.__init__(self)
		self._active = True
		self._socket = socket
		self._callback = callback
		self._buffer = bytearray()

	def run(self):
		while self._active:
			try:
				data = self._socket.recv(4096)
			except ConnectionResetError as e:
				self._log.error("Connection reset: %s" % (str(e)))
				break
			if len(data) == 0:
				# Connection interrupted
				break
			self._buffer += data
			splitbuf = self._buffer.split(b"\r\n")
			self._buffer = splitbuf[-1]
			for rxmsg in splitbuf[:-1]:
				self._callback(rxmsg)
		self._active = False

	@property
	def connected(self):
		return self._active

	def quit(self):
		self._active = False

class RXBuffer(object):
	def __init__(self):
		self._rx_thread = None
		self._buf = queue.Queue()
		self._socket = None

	def readfrom(self, socket):
		if self._rx_thread is not None:
			self._rx_thread.quit()
		self._rx_thread = _ReadingWorkerThread(socket, self.put)
		self._rx_thread.start()

	@property
	def connected(self):
		return (self._rx_thread is not None) and self._rx_thread.connected

	def put(self, rxdata):
		self._buf.put(rxdata)

	def get(self, timeout):
		try:
			return self._buf.get(timeout = timeout)
		except queue.Empty:
			return None

	def close(self):
		if self._rx_thread is not None:
			self._rx_thread.quit()

