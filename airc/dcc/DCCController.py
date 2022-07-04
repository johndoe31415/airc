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

	async def _handle_request_async(self, irc_client, dcc_request):
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
		# transfer.
		filesize = os.stat(spoolfile).st_size

		if dcc_request.is_active:
			if filesize == 0:
				# Simply connect to target and download the file.
				(reader, writer) = await asyncio.open_connection(host = str(dcc_request.ip), port = dcc_request.port)

		try:
			await self._download_loop(dcc_request, spoolfile, filesize, reader, writer)

			# Transfer completed, move spoolfile to download dir
			destination = self._determine_final_filename(destination)
			shutil.move(spoolfile, destination)
		except DCCTransferAbortedException:
			# Transfer aborted, move spoolfile to stale
			TODO


	def handle_request(self, irc_client, dcc_request):
		asyncio.ensure_future(self._handle_request_async(irc_client, dcc_request))
