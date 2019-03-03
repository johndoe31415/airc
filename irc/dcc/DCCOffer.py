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

import re
import uuid
import logging

from .DCCRecvTransfer import DCCRecvTransfer
from .DCCEnums import DCCTransferType

class DCCOffer(object):
	_DISALLOWED_FILENAME_CHARS = re.compile("[^-A-Za-z0-9_.]")

	_log = logging.getLogger("irc.DCCOffer")
	def __init__(self, dcc_ctrlr, transfer_type, origin, filename, filesize_bytes, ip, port, debugging = False):
		assert(isinstance(transfer_type, DCCTransferType))
		self._dcc_ctrlr = dcc_ctrlr
		self._offerid = uuid.uuid4()
		self._transfer_type = transfer_type
		self._origin = origin
		self._filename = filename
		self._filesize_bytes = filesize_bytes
		self._ip = ip
		self._port = port
		self._debugging = debugging
		self._xfer_id = None
		self._transfer = None

	@property
	def offerid(self):
		return self._offerid

	@property
	def xfer_id(self):
		return self._xfer_id

	@property
	def transfer_type(self):
		return self._transfer_type

	@property
	def origin(self):
		return self._origin

	@property
	def filename(self):
		return self._filename

	@property
	def sanitized_filename(self):
		return self._DISALLOWED_FILENAME_CHARS.sub("_", self.filename)

	@property
	def filesize_bytes(self):
		return self._filesize_bytes

	@property
	def ip(self):
		return self._ip

	@property
	def port(self):
		return self._port

	@property
	def transfer(self):
		return self._transfer

	def _accept_active(self, local_filename):
		return DCCRecvTransfer(self, local_filename, debugging = self._debugging)

	def _accept_passive(self, local_filename):
		passive_endpoint = self._dcc_ctrlr.get_listening_socket()
		if passive_endpoint is None:
			self._log.error("No listening socket available, cannot accept passive transfer.")
			return

		(listening_ip, listening_port, socket) = passive_endpoint
		self._log.info("Allocated listening socket for incoming passive transfer on %s:%d.", listening_ip, listening_port)
		return DCCRecvTransfer(self, local_filename, passive_endpoint = passive_endpoint, debugging = self._debugging)

	def accept(self, local_filename, xfer_id = None):
		if self.transfer_type == DCCTransferType.Active:
			self._transfer = self._accept_active(local_filename)
		else:
			self._transfer = self._accept_passive(local_filename)
		self._xfer_id = xfer_id
		if xfer_id is not None:
			self._log.debug("Xfer ID %s is internally handled as offer ID %s", xfer_id, self.offerid)
		self._dcc_ctrlr.new_transfer(self)

	def __str__(self):
		return "DCCOffer<%s from %s, \"%s\", %d bytes, %s:%d>" % (self.transfer_type.name, self.origin, self.filename, self.filesize_bytes, self.ip, self.port)

