#!/usr/bin/python3
#	airc - Python asynchronous IRC client library with DCC support
#	Copyright (C) 2016-2022 Johannes Bauer
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

import sys
import os
import airc
import asyncio
import logging
from FriendlyArgumentParser import FriendlyArgumentParser

class SimpleIRCClient():
	def __init__(self, args):
		self._args = args
		self._setup_logging()

	def _setup_logging(self):
		if self._args.verbose == 0:
			loglevel = logging.WARNING
		elif self._args.verbose == 1:
			loglevel = logging.INFO
		elif self._args.verbose == 2:
			loglevel = logging.DEBUG
		elif self._args.verbose == 3:
			loglevel = logging.TRACE
		else:
			loglevel = logging.EAVESDROP
		logging.basicConfig(format = "{name:>40s} [{levelname:.2s}]: {message}", style = "{", level = loglevel)

	async def main(self):
		irc_server = airc.IRCServer(hostname = self._args.hostname, port = self._args.port, use_tls = self._args.use_tls)
		irc_servers = [ irc_server ]
		if len(self._args.nickname) == 0:
			identities = [ airc.IRCIdentity(nickname = "x" + os.urandom(4).hex()) ]
		else:
			identities = [ airc.IRCIdentity(nickname = nickname) for nickname in self._args.nickname ]
		idgen = airc.ListIRCIdentityGenerator(identities)
		network = airc.IRCNetwork(irc_client_class = airc.client.RawIRCClient, irc_servers = irc_servers, identity_generator = idgen)
		task = network.task()
		await task

parser = FriendlyArgumentParser(description = "Simple IRC client.")
parser.add_argument("-H", "--hostname", metavar = "hostname", default = "irc.freenode.org", help = "Specifies hostname to connect to. Defaults to %(default)s.")
parser.add_argument("-p", "--port", metavar = "port", type = int, default = 6666, help = "Specifies port to connect to. Defaults to %(default)d.")
parser.add_argument("-s", "--use-tls", action = "store_true", help = "Connect using TLS to the server.")
parser.add_argument("-n", "--nickname", metavar = "nick", action = "append", default = [ ], help = "Nickname(s) to use. Multiple fallbacks can be specified. By default, a randomized nickname is used.")
parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
args = parser.parse_args(sys.argv[1:])

sic = SimpleIRCClient(args)
asyncio.run(sic.main())
