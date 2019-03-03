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

import os
import time
import logging
import collections
from .DCCEnums import DCCTransferState, DCCTransferType, DCCConnectionState
from .DCCRecvThread import DCCRecvThread
from .Helpers import Helpers

class DCCRecvTransfer(object):
	_PASSIVE_TRANSFER_RESUME_TIMEOUT_SECS = 120

	_log = logging.getLogger("irc.DCCRecvTransfer")
	_ActivePeerAddress = collections.namedtuple("ActivePeerAddress", [ "addrtype", "hostname", "port" ])
	_PassivePeerAddress = collections.namedtuple("PassivePeerAddress", [ "addrtype", "socket" ])

	def __init__(self, offer, local_filename, passive_endpoint = None, debugging = False):
		if (offer.transfer_type == DCCTransferType.Passive) and (passive_endpoint is None):
			raise Exception("Receive of passive transfer requested, but no listening port/socket was allocated.")
		self._offer = offer
		self._local_filename = local_filename
		self._state = DCCTransferState.OFFER_RECEIVED
		self._timeout = None
		self._passive_endpoint = passive_endpoint
		self._debugging = debugging
		self._transfer_thread = None
		(self._start_xfer_offset, self._f) = self._open_file()

	def _open_file(self):
		start_offset = 0
		if os.path.isfile(self._local_filename):
			current_filesize = os.stat(self._local_filename).st_size
			if current_filesize < self._offer.filesize_bytes:
				start_offset = current_filesize
				f = open(self._local_filename, "r+b")
				f.seek(0, os.SEEK_END)
			else:
				if current_filesize == self._offer.filesize_bytes:
					self._log.warn("%s: File %s already exists locally, but is already complete, marking transfer as finished.", self, self._local_filename)
					self._state = DCCTransferState.FINISHED
				else:
					self._log.error("%s: File %s already exists locally, but is with its %d bytes greater than the offered %d bytes file, aborting transfer.", self, self._local_filename, current_filesize, self._offer.filesize_bytes)
					self._state = DCCTransferState.FAILED
				f = None
		else:
			f = open(self._local_filename, "wb")
		return (start_offset, f)

	@property
	def speed(self):
		if self._transfer_thread is None:
			return 0
		else:
			return self._transfer_thread.speed

	@property
	def position(self):
		if self._transfer_thread is None:
			return self._start_xfer_offset
		else:
			return self._start_xfer_offset + self._transfer_thread.transferred

	@property
	def state(self):
		return self._state

	@property
	def start_xfer_offset(self):
		return self._start_xfer_offset

	@property
	def is_done(self):
		return self._state in [ DCCTransferState.FINISHED, DCCTransferState.FAILED ]

	@property
	def want_resume(self):
		return self._start_xfer_offset > 0

	def _start_transfer(self, socket = None):
		if self._offer.transfer_type == DCCTransferType.Active:
			peer_address = self._ActivePeerAddress(addrtype = self._offer.transfer_type, hostname = self._offer.ip, port = self._offer.port)
		else:
			peer_address = self._PassivePeerAddress(addrtype = self._offer.transfer_type, socket = socket)
		self._transfer_thread = DCCRecvThread(self._offer.xfer_id, peer_address, self._f, self._start_xfer_offset, self._offer.filesize_bytes, debugging = self._debugging)
		self._transfer_thread.start()

	def communicate(self, connection):
		if self._offer.transfer_type == DCCTransferType.Active:
			if ((self._state == DCCTransferState.OFFER_RECEIVED) and (not self.want_resume)) or ((self._state == DCCTransferState.RESUME_CONFIRMED) and (self.want_resume)):
				# Directly request the file. Make the connection.
				self._start_transfer()
				self._state = DCCTransferState.TRANSFERRING
				self._log.info("%s: Requesting file in active transfer", self)
			elif (self._state == DCCTransferState.OFFER_RECEIVED) and (self.want_resume):
				# Request resume at position.
				connection.send_ctcp(self._offer.origin.nickname, "DCC RESUME %s %d %d" % (self._offer.filename, self._offer.port, self._start_xfer_offset))
				self._state = DCCTransferState.RESUME_REQUESTED
				self._timeout = time.time() + self._PASSIVE_TRANSFER_RESUME_TIMEOUT_SECS
				self._log.info("%s: Requesting resume of active transfer", self)
		else:
			if ((self._state == DCCTransferState.OFFER_RECEIVED) and (not self.want_resume)) or ((self._state == DCCTransferState.RESUME_CONFIRMED) and (self.want_resume)):
				# Directly request the file. Make the connection.
				(listening_ip, listening_port, listening_socket) = self._passive_endpoint
				self._start_transfer(listening_socket)
				time.sleep(0.1)
				connection.send_ctcp(self._offer.origin.nickname, "DCC SEND %s %d %d %d %d" % (self._offer.filename, Helpers.ipv4_to_int(listening_ip), listening_port, self._offer.filesize_bytes, self._offer.port))
				self._state = DCCTransferState.TRANSFERRING
				self._log.info("%s: Requesting file in passive transfer", self)
			elif (self._state == DCCTransferState.OFFER_RECEIVED) and (self.want_resume):
				# Request resume at position.
				connection.send_ctcp(self._offer.origin.nickname, "DCC RESUME %s %d %d" % (self._offer.filename, self._offer.port, self._start_xfer_offset))
				self._state = DCCTransferState.RESUME_REQUESTED
				self._timeout = time.time() + self._PASSIVE_TRANSFER_RESUME_TIMEOUT_SECS
				self._log.info("%s: Requesting resume of passive transfer", self)

		if self._state == DCCTransferState.RESUME_REQUESTED:
			now = time.time()
			if now > self._timeout:
				self._log.info("%s: Resume request timed out. Marking transfer as interrupted.", self)
				self._state = DCCTransferState.INTERRUPTED
				if self._passive_endpoint is not None:
					(listening_ip, listening_port, listening_socket) = self._passive_endpoint
					listening_socket.close()

		if self._state == DCCTransferState.TRANSFERRING:
			# Check if finished
			if not (self._transfer_thread.state == DCCConnectionState.Active):
				if self._transfer_thread.successful:
					self._log.info("%s: Successfully finished transfer of %s from %s.", self, self._offer.filename, self._offer.origin.nickname)
					self._state = DCCTransferState.FINISHED
				else:
					self._log.info("%s: Interrupted transfer of %s from %s: %s", self, self._offer.filename, self._offer.origin.nickname, self._transfer_thread.state)
					self._state = DCCTransferState.INTERRUPTED

	def confirm_resume(self, position):
		if self._state != DCCTransferState.RESUME_REQUESTED:
			self._log.error("%s: Peer confirmed resume, but we never requested it. Ignoring.", self)
			self._state = DCCTransferState.FAILED
			return

		if position != self._start_xfer_offset:
			self._log.error("%s: Requested resume at %d, but peer offered resume at %d. Aborting transfer.", self, self._start_xfer_offset, position)
			self._state = DCCTransferState.FAILED
			return
		self._log.info("%s: Peer correctly confirmed resume at offset %d", self, position)
		self._state = DCCTransferState.RESUME_CONFIRMED

	def __str__(self):
		return "RecvTransfer<%s>" % (self._offer.xfer_id)

