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

class AsyncIRCException(Exception): pass
class OutOfValidNicknamesException(AsyncIRCException): pass
class ServerSeveredConnectionException(AsyncIRCException): pass
class ServerMessageParseException(AsyncIRCException): pass
class InvalidOriginException(AsyncIRCException): pass

class DCCTransferException(AsyncIRCException): pass
class DCCRequestParseException(DCCTransferException): pass
class DCCTransferAbortedException(DCCTransferException): pass
class DCCTransferTimeoutException(DCCTransferException): pass
class DCCTransferDataMismatchException(DCCTransferException): pass
class DCCPassiveTransferUnderconfiguredException(DCCTransferException): pass
class DCCPassivePortsExhaustedException(DCCTransferException): pass
class DCCResourcesExhaustedException(DCCTransferException): pass
