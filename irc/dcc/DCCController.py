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

import logging
import re
import socket

from .Helpers import Helpers
from .DCCOffer import DCCOffer
from .DCCEnums import DCCTransferType, DCCTransferState

class DCCController(object):
	_log = logging.getLogger("irc.DCCTransfers")
	_ACTIVE_DCC_SEND_MSG = re.compile("DCC SEND (?P<filename>[^ ]+) (?P<ip>\d+) (?P<port>\d+) (?P<filesize>\d+)", flags = re.IGNORECASE)
	_PASSIVE_DCC_SEND_MSG = re.compile("DCC SEND (?P<filename>[^ ]+) (?P<firewalled_ip>\d+) 0 (?P<filesize>\d+) (?P<token>\d+)", flags = re.IGNORECASE)
	_ACTIVE_DCC_CONFIRM_RESUME_MSG = re.compile("DCC ACCEPT (?P<filename>[^ ]+) (?P<port>\d+) (?P<position>\d+)", flags = re.IGNORECASE)
	_PASSIVE_DCC_CONFIRM_RESUME_MSG = re.compile("DCC ACCEPT (?P<filename>[^ ]+) \d+ (?P<position>\d+) (?P<token>\d+)", flags = re.IGNORECASE)

	def __init__(self, connection, passive_port_range = None, debugging = False):
		self._connection = connection
		if passive_port_range is None:
			self._passive_port_range = [ ]
		else:
			self._passive_port_range = list(passive_port_range)
		self._offers = { }
		self._local_ip = None
		self._debugging = debugging

	def set_local_ip(self, ip):
		self._local_ip = ip

	def new_transfer(self, offer):
		self._offers[offer.offerid] = offer

	def _handle_active_dcc_offer(self, origin, filename, filesize_bytes, ip, port):
		self._log.info("%s offered us a file using active DCC called '%s' with size %d bytes at %s:%d" % (origin, filename, filesize_bytes, ip, port))
		offer = DCCOffer(self, DCCTransferType.Active, origin, filename, filesize_bytes, ip, port, debugging = self._debugging)
		self._connection.perform_callback("incoming-dcc", offer)

	def get_listening_socket(self):
		if self._local_ip is None:
			return None
		port_count = len(self._passive_port_range)
		if port_count == 0:
			return None
		sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		for i in range(port_count):
			port = self._passive_port_range.pop(0)
			self._passive_port_range.append(port)
			try:
				sd.bind(("0.0.0.0", port))
			except (PermissionError, OSError):
				continue
			break
		else:
			sd.close()
			return None
		self._log.debug("Allocated listening socket: %s:%d -> %s", self._local_ip, port, sd)
		return (self._local_ip, port, sd)

	def _handle_passive_dcc_offer(self, origin, filename, filesize_bytes, firewalled_ip, token):
		self._log.info("%s offered us a file using passive DCC called '%s' with size %d bytes. Request token %d, firewalled IP %s" % (origin, filename, filesize_bytes, token, firewalled_ip))
		if self._local_ip is None:
			self._log.error("Passive DCC transfer failed: Local IP address is unknown, cannot intiate transfer.")
			return
		offer = DCCOffer(self, DCCTransferType.Passive, origin, filename, filesize_bytes, firewalled_ip, token, debugging = self._debugging)
		self._connection.perform_callback("incoming-dcc", offer)

	def _handle_resume(self, origin, filename, position, token_port):
		for offer in self._offers.values():
			if (offer.filename == filename) and (origin == offer.origin) and (offer.port == token_port) and (offer.transfer.state == DCCTransferState.RESUME_REQUESTED) and (offer.transfer.start_xfer_offset == position):
				break
		else:
			self._log.error("Resume offered: %s \"%s\" at %d token/port %d -- no such transfer known.", origin, filename, position, token_port)
			return
		offer.transfer.confirm_resume(position)

	def _handle_active_dcc_confirm_resume(self, origin, filename, position, port):
		self._log.info("%s confirmed active transfer resume of %s at position %d, port %d." % (origin, filename, position, port))
		self._handle_resume(origin, filename, position, port)

	def _handle_passive_dcc_confirm_resume(self, origin, filename, position, token):
		self._log.info("%s confirmed passive transfer resume of %s at position %d, token %d." % (origin, filename, position, token))
		self._handle_resume(origin, filename, position, token)

	def time_tick(self):
		cleanup = [ ]
		for (offer_id, offer) in self._offers.items():
			offer.transfer.communicate(self._connection)
			if offer.transfer.state in [ DCCTransferState.FINISHED, DCCTransferState.INTERRUPTED, DCCTransferState.FAILED ]:
				cleanup.append(offer_id)
#			print("Progress:", offer.transfer)
		for offer_id in cleanup:
			self._log.debug("Cleaning up entry %s", offer_id)
			self._connection.perform_callback("finished-dcc", self._offers[offer_id])
			del self._offers[offer_id]

	def handle(self, origin, target, message):
		self._log.debug("DCC CTCP received from %s: %s", origin, message)

		result = self._ACTIVE_DCC_SEND_MSG.fullmatch(message)
		if result:
			result = result.groupdict()
			ip = Helpers.int_to_ipv4(int(result["ip"]))
			port = int(result["port"])
			filesize_bytes = int(result["filesize"])
			self._handle_active_dcc_offer(origin, result["filename"], filesize_bytes, ip, port)
			return

		result = self._PASSIVE_DCC_SEND_MSG.fullmatch(message)
		if result:
			result = result.groupdict()
			firewalled_ip = Helpers.int_to_ipv4(int(result["firewalled_ip"]))
			filesize_bytes = int(result["filesize"])
			token = int(result["token"])
			self._handle_passive_dcc_offer(origin, result["filename"], filesize_bytes, firewalled_ip, token)
			return

		result = self._ACTIVE_DCC_CONFIRM_RESUME_MSG.fullmatch(message)
		if result:
			result = result.groupdict()
			self._handle_active_dcc_confirm_resume(origin, result["filename"], int(result["position"]), int(result["port"]))
			return

		result = self._PASSIVE_DCC_CONFIRM_RESUME_MSG.fullmatch(message)
		if result:
			result = result.groupdict()
			self._handle_passive_dcc_confirm_resume(origin, result["filename"], int(result["position"]), int(result["token"]))
			return

		self._log.warn("Cannot handle strange incoming CTCP DCC message from %s -> %s \"%s\"", origin, target, message)

	def __iter__(self):
		return iter(self._offers.values())
