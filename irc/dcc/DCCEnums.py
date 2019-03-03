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

import enum

class DCCTransferType(enum.IntEnum):
	Active = 1
	Passive = 2

class DCCTransferState(enum.IntEnum):
	OFFER_RECEIVED = 0
	RESUME_REQUESTED = 1
	RESUME_CONFIRMED = 2
	TRANSFERRING = 3
	FINISHED = 4
	FAILED = 5
	INTERRUPTED = 6

class DCCConnectionState(enum.IntEnum):
	Active = 1
	ConnectionInterrupted = 2
	ConnectionClosedByPeer = 3
	ConnectionTimeout = 4
	Finished = 5
