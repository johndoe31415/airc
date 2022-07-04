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

import enum

class IRCTimeout(enum.IntEnum):
	RegistrationTimeoutSecs = 0
	ReconnectTimeAfterNicknameExhaustionSecs = 1
	ReconnectTimeAfterConnectionErrorSecs = 2
	ReconnectTimeAfterSeveredConnectionSecs = 3
	ReconnectTimeAfterServerParseExceptionSecs = 4
	ReconnectTimeAfterTLSErrorSecs = 5
	JoinChannelTimeoutSecs = 6
	RejoinChannelTimeSecs = 7
	DCCAckResumeTimeoutSecs = 8

class IRCCallbackType(enum.Enum):
	PrivateMessage = "privmsg"
	Notice = "notice"
	CTCPRequest = "ctcp_request"
	CTCPReply = "ctcp_reply"
	IncomingDCCRequest = "dcc_xfer_request"
	DCCTransferStarted = "dcc_xfer_started"

class Usermode(enum.IntEnum):
	Regular = 0
	Voice = 1
	Op = 2

class DCCMessageType(enum.IntEnum):
	Send = 0
	Accept = 1
