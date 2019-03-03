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

import threading
import logging
import struct
import socket
import time
import select

from .DCCEnums import DCCTransferType, DCCConnectionState
from .SpeedAverager import SpeedAverager
from irc.FilesizeFormatter import FilesizeFormatter

class TransferFailedException(Exception): pass

class DCCRecvThread(threading.Thread):
	_log = logging.getLogger("irc._DCCRecvThread")
	_MAX_CHUNKSIZE = 128 * 1024
	_REPLY = struct.Struct(">L")
	_FILESIZE_FMT = FilesizeFormatter(base1000 = True)

	def __init__(self, xfer_id, peer_address, f, start_offset, total_size, debugging = False):
		threading.Thread.__init__(self)
		self._socket = None
		self._xfer_id = xfer_id
		self._peer_address = peer_address
		self._f = f
		self._start_offset = start_offset
		self._total_size = total_size
		self._debugging = debugging
		self._transferred_bytes = 0
		self._speed_averager = SpeedAverager()
		self._stall_timeout = SpeedAverager(min_secs = 5, average_secs = 120)
		self._state = DCCConnectionState.Active

	@property
	def transferred(self):
		return self._transferred_bytes

	@property
	def state(self):
		return self._state

	@property
	def remaining_bytes(self):
		return self._total_size - self._start_offset - self._transferred_bytes

	@property
	def successful(self):
		return self.remaining_bytes == 0

	@property
	def speed(self):
		return self._speed_averager.speed

	@staticmethod
	def _nonblocking_accept(sd, timeout_secs):
		(readable, writable, errored) = select.select([ sd ], [ ], [ ], timeout_secs)
		if len(readable) > 0:
			return readable[0].accept()

	def _nonblocking_recv(self, sd, length, timeout_secs):
		(readable, writable, errored) = select.select([ sd ], [ ], [ ], timeout_secs)
		if len(readable) > 0:
			data = sd.recv(length)
			if len(data) == 0:
				raise TransferFailedException("Peer closed the connection.")
			if self._debugging:
				# Throttle connection
				time.sleep(1.5)
			return data
		else:
			return b""

	def _initiate_connection(self):
		if self._peer_address.addrtype == DCCTransferType.Active:
			try:
				self._socket = socket.create_connection((self._peer_address.hostname, self._peer_address.port))
			except (TimeoutError, ConnectionRefusedError) as e:
				raise TransferFailedException("Could not connect to active DCC at %s:%d (%s); aborting." % (self._peer_address.hostname, self._peer_address.port, str(e)))
		else:
			timeout = 120
			self._log.debug("%s: Waiting %d seconds for incoming connection to start passive transfer", self, timeout)
			self._peer_address.socket.listen(1)
			peer = self._nonblocking_accept(self._peer_address.socket, timeout)
			if peer is not None:
				(self._socket, (peer_ip, peer_port)) = peer
				self._log.info("%s: Accepted incoming connection for passive transfer from %s:%d" % (self, peer_ip, peer_port))
			else:
				raise TransferFailedException("Timeout in accept(): No incoming connection after timeout period of %d seconds." % (timeout))

	def _perform_download(self):
		try:
			while self.remaining_bytes > 0:
				chunksize = self.remaining_bytes
				if chunksize > self._MAX_CHUNKSIZE:
					chunksize = self._MAX_CHUNKSIZE
				data = self._nonblocking_recv(self._socket, chunksize, 5)
				self._transferred_bytes += len(data)
				self._speed_averager.add(self._transferred_bytes)
				self._stall_timeout.add(self._transferred_bytes)
				speed = self._stall_timeout.real_speed
				if (speed is not None) and (speed < 1):
					raise TransferFailedException("Download stalled, aborting.")

				if len(data) > 0:
					self._f.write(data)
					self._socket.send(self._REPLY.pack(self._transferred_bytes & 0xffffffff))
		except (ConnectionResetError, BrokenPipeError) as e:
			raise TransferFailedException("Connection unexpectedly reset by peer: %s" % (str(e)))

	def _cleanup(self):
		self._f.flush()
		self._f.close()
		if self._socket is not None:
			try:
				self._socket.shutdown(socket.SHUT_RDWR)
			except OSError:
				pass
			self._socket.close()
		if self._peer_address.addrtype == DCCTransferType.Passive:
			if self._peer_address.socket is not None:
				self._peer_address.socket.close()

	def run(self):
		self._log.debug("%s: Started transfer thread.", self)
		try:
			self._initiate_connection()
			self._perform_download()
		except TransferFailedException as e:
			self._log.error("%s: %s", self, str(e))

		if self.remaining_bytes == 0:
			new_state = DCCConnectionState.Finished
		else:
			new_state = DCCConnectionState.ConnectionInterrupted

		if self.remaining_bytes == 0:
			new_state = DCCConnectionState.Finished

		self._log.info("%s: Transfer finished (%s): %d bytes at %s/s. %d bytes remaining.", self, new_state.name, self._transferred_bytes, self._FILESIZE_FMT(round(self.speed)), self.remaining_bytes)
		self._cleanup()
		self._state = new_state

	def __str__(self):
		return "DCCRecvThread<%s>" % (self._xfer_id)
