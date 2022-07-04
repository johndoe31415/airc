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

import re
import os
import logging
import asyncio
import contextlib
import base64
import shutil
import struct
from airc.dcc.DCCConfiguration import DCCConfiguration
from airc.dcc.DCCRequest import DCCRequestParser
from airc.Tools import AsyncTools
from airc.Exceptions import DCCTransferAbortedException, DCCTransferDataMismatchException, DCCTransferTimeoutException
from airc.ExpectedResponse import ExpectedResponse
from airc.Enums import IRCTimeout

_log = logging.getLogger(__spec__.name)

class DCCController():
	_FILENAME_SAFECHARS = re.compile(r"[^A-Za-z0-9._-]")
	_ACK_MSG = struct.Struct("> L")

	def __init__(self, dcc_configuration: DCCConfiguration):
		self._config = dcc_configuration
		with contextlib.suppress(FileExistsError):
			os.makedirs(self.config.download_spooldir_stale)
		with contextlib.suppress(FileExistsError):
			os.makedirs(self.config.download_spooldir_active)
		self._move_active_downloads_to_stale()
		if self.config.passive_portrange is None:
			self._passive_ports = [ ]
		else:
			self._passive_ports = list(range(self.config.passive_portrange[0], self.config.passive_portrange[1] + 1))

	def _move_active_downloads_to_stale(self):
		# TODO implement me
		pass

	@property
	def config(self):
		return self._config

	def _sanitize_filename(self, filename):
		# Sanitize filename first
		sanitized_filename = self._FILENAME_SAFECHARS.sub("_", filename)
		sanitized_filename = sanitized_filename.strip("_")
		if sanitized_filename == "":
			sanitized_filename = "_"
		return sanitized_filename

	def _async_request_determine_acceptance(self, dcc_request):
		_log.info(f"Handling incoming DCC transfer request {dcc_request}")
		# Someone wants to send us a file. First decide if we want it.
		filename = self._sanitize_filename(dcc_request.filename)
		if not self.config.autoaccept:
			# Let the client make a decision
			decision = airc.dcc.DCCDecision(filename = self.config.autoaccept_download_dir + "/" + filename)
			self.fire_callback(IRCCallbackType.IncomingDCCRequest, dcc_request, decision)
			if not decision.accept:
				# Handler refuses to accept this file.
				_log.info(f"Incoming DCC request {dcc_request} was rejected by handler. Ignoring the request.")
				return None
			destination = decision.filename
			_log.info(f"Incoming DCC request {dcc_request} was accepted by handler, storing to {destination}")
		else:
			destination = self.config.autoaccept_download_dir + "/" + filename
			_log.info(f"Incoming DCC request {dcc_request} was autoaccepted, storing to {destination}")
		return destination

	def _async_request_check_stale_spoolfile(self, dcc_request):
		# Resume the spoolfile that is the largest
		safename = base64.b64encode(dcc_request.filename.encode("utf-8")).decode("ascii")
		spoolfiles = [ ]
		for i in range(100):
			potential_spoolfile = f"{self.config.download_spooldir_stale}/{i:02d}_{dcc_request.filesize}_{safename}"
			try:
				statres = os.stat(potential_spoolfile)
				spoolfiles.append((statres.st_size, potential_spoolfile))
			except FileNotFoundError:
				pass

		if len(spoolfiles) == 0:
			return

		# Return the largest of the spoolfiles, which has the most promise
		spoolfiles.sort(reverse = True)
		return spoolfiles[0][1]

	def _async_request_get_active_spoolfile(self, dcc_request):
		safename = base64.b64encode(dcc_request.filename.encode("utf-8")).decode("ascii")
		for i in range(100):
			potential_spoolfile = f"{self.config.download_spooldir_active}/{i:02d}_{dcc_request.filesize}_{safename}"
			if not os.path.exists(potential_spoolfile):
				return potential_spoolfile
		return None

	def _async_request_get_spoolfile(self, dcc_request):
		# Check if there already exists a spool file (that the downloaded
		# progress is sent to). If so, move it into the active state and
		# attempt to resume.
		stale_spoolfile = self._async_request_check_stale_spoolfile(dcc_request)
		active_spoolfile = self._async_request_get_active_spoolfile(dcc_request)

		if active_spoolfile is None:
			_log.error(f"Could not find an appropriate spoolfile for download of {dcc_request}.")
			return

		if stale_spoolfile is not None:
			shutil.move(stale_spoolfile, active_spoolfile)
		else:
			# Create an empty file
			with open(active_spoolfile, "wb") as f:
				pass
		return active_spoolfile

	async def _download_loop(self, dcc_request, spoolfile, seek_pos, reader, writer):
		max_chunksize = 256 * 1024
		with open(spoolfile, "ab") as f:
			f.truncate(seek_pos)
			f.seek(seek_pos)
			while f.tell() < dcc_request.filesize:
				chunk = await reader.read(max_chunksize)
				if len(chunk) == 0:
					raise DCCTransferAbortedException(f"Peer closed connection of DCC transfer {dcc_request} after {f.tell()} bytes.")
				f.write(chunk)

				if not dcc_request.turbo:
					ack_msg = self._ACK_MSG.pack(f.tell() & 0xffffffff)
					writer.write(ack_msg)
		_log.info(f"DCC transfer finished successfully: {dcc_request}")

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

	@staticmethod
	def _round_down(value, boundary):
		value = value - boundary
		if value < 0:
			value = 0
		value = value // boundary
		value = value * boundary
		return value

	async def _handle_request_async(self, irc_client, nickname, dcc_request):
		# Check if we want to accept this file in the first place and, if so,
		# where to (tentatively) store it.
		destination = self._async_request_determine_acceptance(dcc_request)
		if destination is None:
			# We don't want this file.
			return

		spoolfile = self._async_request_get_spoolfile(dcc_request)
		if spoolfile is None:
			# Some error occured.
			return

		# Check size of spoolfile to determine if we need to resume the
		# transfer. Discard at least the last n bytes, then round to the
		# closest n byte boundary so that garbage caused by broken transfers
		# hopefully don't affect us.
		resume_offset = os.stat(spoolfile).st_size
		if self.config.discard_tail_at_resume > 0:
			resume_offset = self._round_down(resume_offset, 128 * 1024)

		if resume_offset != 0:
			# Resume request before we connect
			text = f"DCC RESUME {dcc_request.filename} {dcc_request.port} {resume_offset}"
			if dcc_request.is_passive:
				text += f" {dcc_request.passive_token}"
			try:
				response = await asyncio.wait_for(irc_client.ctcp_request(nickname, text, expect = ExpectedResponse.on_privmsg_from(nickname = nickname, ctcp_message = True)), timeout = irc_client.config.timeout(IRCTimeout.DCCAckResumeTimeoutSecs))
			except asyncio.exceptions.TimeoutError:
				raise DCCTransferTimeoutException(f"DCC RESUME was never acknowledged by peer {nickname}, refusing to start transfer.")
			response = DCCRequestParser.parse(response[0].get_param(1)[1 : -1])
			if (response.filename != dcc_request.filename) or (response.port != dcc_request.port) or (response.resume_offset != resume_offset) or (response.passive_token != dcc_request.passive_token):
				# TODO: Technically, there's a small chance this can happen
				# if we get two concurrent resumption messages from the
				# same peer; it is quite unlikely, however, so we'll keep
				# this as is for now. Technically, we should then await
				# another response until we get definitive timeout.
				raise DCCTransferDataMismatchException(f"DCC request {dcc_request} and resumption confirmation {response} do not fit together, refusing to resume transfer.")

		if dcc_request.is_active:
			if resume_offset == 0:
				_log.info(f"Starting active DCC transfer from {nickname}")
			else:
				_log.info(f"Resuming active DCC transfer from {nickname} at offset {resume_offset}")
			(reader, writer) = await asyncio.open_connection(host = str(dcc_request.ip), port = dcc_request.port)
		else:
			if not self.config.enable_passive:
				_log.error(f"Passive DCC transfer requested in {dcc_request}, but passive transfers are disabled.")
				return

			for _ in range(len(self._passive_ports)):
				try:
					passive_port = self._passive_ports.pop(0)
					(server, future) = await AsyncTools.accept_single_connection(host = None, port = passive_port)
					break
				finally:
					self._passive_ports.append(passive_port)
			else:
				_log.error(f"Passive DCC transfer requested in {dcc_request}, but all passive ports exhausted. Cannot transfer.")
				return

			# Let the peer know which port we're listening on
			irc_client.ctcp_request(nickname, f"DCC SEND {dcc_request.filename} {int(self.config.passive_ip)} {passive_port} {dcc_request.filesize} {dcc_request.passive_token}")
			try:
				(reader, writer) = await asyncio.wait_for(future, timeout = irc_client.config.timeout(IRCTimeout.DCCPassiveConnectTimeoutSecs))

				if resume_offset == 0:
					_log.info(f"Starting passive DCC transfer from {nickname}")
				else:
					_log.info(f"Resuming passive DCC transfer from {nickname} at offset {resume_offset}")

			except asyncio.exceptions.TimeoutError:
				raise DCCTransferTimeoutException(f"DCC passive connection on port {passive_port} was never established by peer, timed out.")
			finally:
				server.close()

		try:
			await self._download_loop(dcc_request, spoolfile, resume_offset, reader, writer)

			# Transfer completed, move spoolfile to download dir
			destination = self._determine_final_filename(destination)
			shutil.move(spoolfile, destination)
		except DCCTransferAbortedException:
			# Transfer aborted, move spoolfile to stale
			TODO


	def handle_request(self, irc_client, nickname, dcc_request):
		asyncio.ensure_future(self._handle_request_async(irc_client, nickname, dcc_request))
