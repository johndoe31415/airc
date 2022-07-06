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

import os
import re
import struct
import base64
import logging
import asyncio
import contextlib
import shutil
import time
from airc.dcc.DCCDecision import DCCDecision
from airc.dcc.DCCRequest import DCCRequestParser
from airc.Exceptions import DCCTransferAbortedException, DCCTransferDataMismatchException, DCCTransferTimeoutException, DCCResourcesExhaustedException, DCCPassiveTransferUnderconfiguredException
from airc.Tools import NumberTools
from airc.ExpectedResponse import ExpectedResponse
from airc.Enums import IRCTimeout, IRCCallbackType
from airc.FilesizeFormatter import FilesizeFormatter

_log = logging.getLogger(__spec__.name)

class DCCRecvTransfer():
	_FILENAME_SAFECHARS = re.compile(r"[^A-Za-z0-9._-]")
	_ACK_MSG = struct.Struct("> L")
	_FilesizeFormatter = FilesizeFormatter()

	def __init__(self, dcc_controller, irc_client, nickname: str, dcc_request, throttle_bytes_per_sec: float | None = None):
		self._dcc_controller = dcc_controller
		self._irc_client = irc_client
		self._nickname = nickname
		self._dcc_request = dcc_request
		self._spoolname = None
		self._throttle_bytes_per_sec = throttle_bytes_per_sec
		self._transfer_started = None
		self._bytes_transferred = 0

	def average_transfer_speed(self):
		if self._transfer_started is None:
			return None
		now = time.time()
		tdiff = time.time() - self._transfer_started
		if tdiff < 1e-3:
			return None
		return self._bytes_transferred / tdiff

	@property
	def average_transfer_speed_str(self):
		ats = self.average_transfer_speed()
		if ats is None:
			return "N/A"
		else:
			return f"{self._FilesizeFormatter(round(ats))}/sec"

	@property
	def throttle_bytes_per_sec(self):
		return self._throttle_bytes_per_sec

	@throttle_bytes_per_sec.setter
	def throttle_bytes_per_sec(self, value: float):
		self._throttle_bytes_per_sec = value

	@property
	def spoolname(self):
		if self._spoolname is None:
			safename = base64.b64encode(self._dcc_request.filename.encode("utf-8")).decode("ascii")
			self._spoolname = f"{self._dcc_request.filesize}_{safename}"
		return self._spoolname

	def _sanitize_filename(self, filename):
		# Sanitize filename first
		sanitized_filename = self._FILENAME_SAFECHARS.sub("_", filename)
		sanitized_filename = sanitized_filename.strip("_")
		if sanitized_filename == "":
			sanitized_filename = "_"
		return sanitized_filename

	def _determine_acceptance(self):
		_log.info("Handling incoming DCC transfer request %s", self._dcc_request)
		# Someone wants to send us a file. First decide if we want it.
		filename = self._sanitize_filename(self._dcc_request.filename)
		if not self._dcc_controller.config.autoaccept:
			# Let the client make a decision
			decision = DCCDecision(filename = self._dcc_controller.config.autoaccept_download_dir + "/" + filename)
			self._irc_client.fire_callback(IRCCallbackType.IncomingDCCRequest, self._dcc_request, decision)
			if not decision.accept:
				# Handler refuses to accept this file.
				_log.info("Incoming DCC request %s was rejected by handler. Ignoring the request.", self._dcc_request)
				return None
			destination = decision.filename
			_log.info("Incoming DCC request %s was accepted by handler, storing to %s", self._dcc_request, destination)
		else:
			destination = self._dcc_controller.config.autoaccept_download_dir + "/" + filename
			_log.info("Incoming DCC request %s was autoaccepted, storing to %s", self._dcc_request, destination)
		return destination

	def _spooldir_iter(self, path_prefix, must_exist = False):
		for i in range(100):
			potential_spoolfile = f"{path_prefix}/{i:02d}_{self.spoolname}"
			exists = os.path.exists(potential_spoolfile)
			if exists == must_exist:
				yield potential_spoolfile

	def _check_stale_spoolfile(self):
		# Resume the spoolfile that is the largest
		spoolfiles = [ ]
		for potential_spoolfile in self._spooldir_iter(self._dcc_controller.config.download_spooldir_stale, must_exist = True):
			statres = os.stat(potential_spoolfile)
			spoolfiles.append((statres.st_size, potential_spoolfile))

		if len(spoolfiles) == 0:
			return None

		# Return the largest of the spoolfiles, which has the most promise
		spoolfiles.sort(reverse = True)
		return spoolfiles[0][1]

	def _get_unused_active_spoolfile(self):
		try:
			return next(self._spooldir_iter(self._dcc_controller.config.download_spooldir_active))
		except StopIteration:
			raise DCCResourcesExhaustedException(f"Could not find an appropriate unused active spoolfile for download of {self._dcc_request}.")

	def _get_unused_stale_spoolfile(self):
		try:
			return next(self._spooldir_iter(self._dcc_controller.config.download_spooldir_stale))
		except StopIteration:
			raise DCCResourcesExhaustedException(f"Could not find an appropriate unused stale spoolfile for storage of partial {self._dcc_request}.")

	def _create_or_reuse_spoolfile(self):
		# Check if there already exists a spool file (that the downloaded
		# progress is sent to). If so, move it into the active state and
		# attempt to resume.
		stale_spoolfile = self._check_stale_spoolfile()
		active_spoolfile = self._get_unused_active_spoolfile()

		if stale_spoolfile is not None:
			shutil.move(stale_spoolfile, active_spoolfile)
		else:
			# Create an empty file
			with open(active_spoolfile, "wb"):
				pass
		return active_spoolfile

	async def _download_loop(self, spoolfile, resume_offset, reader, writer):
		max_chunksize = 256 * 1024
		with open(spoolfile, "ab") as f:
			f.truncate(resume_offset)
			f.seek(resume_offset)
			while f.tell() < self._dcc_request.filesize:
				chunk = await reader.read(max_chunksize)
				self._bytes_transferred += len(chunk)
				if len(chunk) == 0:
					raise DCCTransferAbortedException("Peer closed connection of DCC transfer {self._dcc_request} after {f.tell()} bytes.")
				f.write(chunk)

				if not self._dcc_request.turbo:
					ack_msg = self._ACK_MSG.pack(f.tell() & 0xffffffff)
					writer.write(ack_msg)

				if self.throttle_bytes_per_sec is not None:
					throttle_delay = max_chunksize / self.throttle_bytes_per_sec
					await asyncio.sleep(throttle_delay)
		_log.info("DCC transfer finished successfully: %s at speed %s", self._dcc_request, self.average_transfer_speed_str)

	def _determine_final_filename(self, filename):
		with contextlib.suppress(FileExistsError):
			os.makedirs(os.path.dirname(filename))

		(prefix, suffix) = os.path.splitext(filename)
		i = 0
		while True:
			if i == 0:
				try_filename = filename
			else:
				try_filename = f"{prefix}_{i}{suffix}"
			if not os.path.exists(try_filename):
				return try_filename
			i += 1

	async def handle(self):
		if self._dcc_request.is_passive and (not self._dcc_controller.config.enable_passive):
			raise DCCPassiveTransferUnderconfiguredException(f"Passive DCC transfer requested in {self._dcc_request}, but passive transfers are disabled.")

		# Check if we want to accept this file in the first place and, if so,
		# where to (tentatively) store it.
		destination = self._determine_acceptance()
		if destination is None:
			# We don't want this file.
			return

		spoolfile = self._create_or_reuse_spoolfile()

		# Check size of spoolfile to determine if we need to resume the
		# transfer. Discard at least the last n bytes, then round to the
		# closest n byte boundary so that garbage caused by broken transfers
		# hopefully don't affect us.
		resume_offset = os.stat(spoolfile).st_size
		if self._dcc_controller.config.discard_tail_at_resume > 0:
			resume_offset = NumberTools.round_down(resume_offset, 128 * 1024)

		if resume_offset != 0:
			# Resume request before we connect
			text = f"DCC RESUME {self._dcc_request.filename} {self._dcc_request.port} {resume_offset}"
			if self._dcc_request.is_passive:
				text += f" {self._dcc_request.passive_token}"
			try:
				response = await asyncio.wait_for(self._irc_client.ctcp_request(self._nickname, text, expect = ExpectedResponse.on_privmsg_from(nickname = self._nickname, ctcp_message = True)), timeout = self._irc_client.config.timeout(IRCTimeout.DCCAckResumeTimeoutSecs))
			except asyncio.exceptions.TimeoutError as e:
				raise DCCTransferTimeoutException(f"DCC RESUME was never acknowledged by peer {self._nickname}, refusing to start transfer.") from e

			ctcp_text = response[0].get_param(1)[1 : -1]
			response = DCCRequestParser.parse(ctcp_text)
			if (response.filename != self._dcc_request.filename) or (response.port != self._dcc_request.port) or (response.resume_offset != resume_offset) or (response.passive_token != self._dcc_request.passive_token):
				# TODO: Technically, there's a small chance this can happen
				# if we get two concurrent resumption messages from the
				# same peer; it is quite unlikely, however, so we'll keep
				# this as is for now. Technically, we should then await
				# another response until we get definitive timeout.
				raise DCCTransferDataMismatchException(f"DCC request {self._dcc_request} and resumption confirmation {response} do not fit together, refusing to resume transfer.")

		if self._dcc_request.is_active:
			if resume_offset == 0:
				_log.info("Starting active DCC transfer from %s", self._nickname)
			else:
				_log.info("Resuming active DCC transfer from %s at offset %d", self._nickname, resume_offset)
			(reader, writer) = await asyncio.open_connection(host = str(self._dcc_request.ip), port = self._dcc_request.port)
		else:
			with await self._dcc_controller.allocate_passive_port() as server:
				# Let the peer know which port we're listening on
				self._irc_client.ctcp_request(self._nickname, f"DCC SEND {self._dcc_request.filename} {int(self._dcc_controller.config.public_ip)} {server.port} {self._dcc_request.filesize} {self._dcc_request.passive_token}")
				try:
					(reader, writer) = await asyncio.wait_for(server, timeout = self._irc_client.config.timeout(IRCTimeout.DCCPassiveConnectTimeoutSecs))

					if resume_offset == 0:
						_log.info("Starting passive DCC transfer from %s", self._nickname)
					else:
						_log.info("Resuming passive DCC transfer from %s at offset %d", self._nickname, resume_offset)

				except asyncio.exceptions.TimeoutError as e:
					raise DCCTransferTimeoutException(f"DCC passive connection on port {server.port} was never established by peer, timed out.") from e

		self._transfer_started = time.time()
		try:
			await self._download_loop(spoolfile, resume_offset, reader, writer)
		except:
			# Transfer aborted, move spoolfile to stale
			shutil.move(spoolfile, self._get_unused_stale_spoolfile())
			raise
		else:
			# Transfer completed, move spoolfile to download dir
			destination = self._determine_final_filename(destination)
			shutil.move(spoolfile, destination)
