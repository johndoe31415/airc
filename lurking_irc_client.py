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
import ipaddress
import random
import json
import collections
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
		class CallbackClass():
			def __init__(self):
				self._replies = collections.Counter()

			@property
			def replies(self):
				return self._replies

			async def on_privmsg(self, irc_client, nickname, text):
				#irc_client.privmsg(nickname, f"you said '{text}', {nickname}, that's not nice")
				pass

			async def on_ctcp_reply(self, irc_client, nickname, text):
				self._replies[text] += 1

		dcc_config = airc.dcc.DCCConfiguration()
		dcc_config.public_ip = ipaddress.IPv4Address("192.168.178.34")
		dcc_config.listening_portrange = (16000, 16050)
		dcc_config.autoaccept = True
		dcc_config.default_rx_throttle_bytes_per_sec = 1000 * 1024

		dcc_ctrlr = airc.dcc.DCCController(dcc_configuration = dcc_config)

		cbc = CallbackClass()
		client_configuration = airc.client.ClientConfiguration()
		if len(self._args.channel) == 0:
			client_configuration.add_autojoin_channel("#mytest")
		else:
			client_configuration.add_autojoin_channels(self._args.channel)
		client_configuration.version = "none of your business"
		client_configuration.time_deviation_secs = 1234
		client_configuration.handle_ctcp_ping = True
		client_configuration.dcc_controller = dcc_ctrlr

		irc_server = airc.IRCServer(hostname = self._args.hostname, port = self._args.port, password = self._args.password, use_ssl = self._args.use_tls)
		irc_servers = [ irc_server ]
		if len(self._args.nickname) > 0:
			identities = [ airc.IRCIdentity(nickname = nickname, username = "bob") for nickname in self._args.nickname ]
			idgen = airc.ListIRCIdentityGenerator(identities)
		else:
			idgen = airc.anonymity.AnonymousIdentityGenerator()
		network = airc.IRCNetwork(irc_client_class = airc.client.BasicIRCClient, irc_servers = irc_servers, identity_generator = idgen, client_configuration = client_configuration)
		network.add_all_listeners(cbc)
		network.start()

		await network.connection_established()

		async def list_channels_join_most_popular():
			channels = await network.client.list_channels()
			channels.sort(key = lambda channel: channel.user_count, reverse = True)
			for channel in channels[:5]:
				client_configuration.add_autojoin_channel(channel.name)

		async def query_users():
			queried_users = set()
			while True:
				if network.client is not None:
					for chan in list(network.client.channels):
						new_users = set(chan.users) - queried_users
						queried_users |= new_users
						new_users = list(new_users)
						random.shuffle(new_users)
						for new_user in new_users:
							network.client.ctcp_request(new_user, self._args.ctcp_message)
							await asyncio.sleep(self._args.delay_between_msgs)
							with open(self._args.outfile, "w") as f:
								json.dump(cbc.replies, f)
							print(cbc.replies)
				await asyncio.sleep(1)

		async def show_state():
			while True:
				if network.client is not None:
					print(network.client.channels)
				await asyncio.sleep(1)


		await asyncio.gather(list_channels_join_most_popular(), query_users(), show_state())

parser = FriendlyArgumentParser(description = "Simple IRC client that sends CTCP queries to clients.")
parser.add_argument("--delay-between-msgs", metavar = "secs", type = int, default = 60, help = "Delay between sending out CTCP messages, in seconds. Defaults to %(default)d.")
parser.add_argument("--ctcp-message", metavar = "name", default = "VERSION", help = "CTCP message to send. Defaults to %(default)s.")
parser.add_argument("-c", "--channel", metavar = "channel", default = [ ], action = "append", help = "Channel to lurk in and query users. Can be specified multiple times. Defaults to #mytest if omitted.")
parser.add_argument("-H", "--hostname", metavar = "hostname", default = "irc.irclink.net", help = "Specifies hostname to connect to. Defaults to %(default)s.")
parser.add_argument("-p", "--port", metavar = "port", type = int, default = 6667, help = "Specifies port to connect to. Defaults to %(default)d.")
parser.add_argument("--password", metavar = "password", help = "Specifies the server password. By default unset.")
parser.add_argument("-s", "--use-tls", action = "store_true", help = "Connect using TLS to the server.")
parser.add_argument("-n", "--nickname", metavar = "nick", action = "append", default = [ ], help = "Nickname(s) to use. Multiple fallbacks can be specified. By default, a randomized nickname is used.")
parser.add_argument("-o", "--outfile", metavar = "file", default = "/tmp/output.json", help = "File to store collected results into. Defaults to %(default)s.")
parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
args = parser.parse_args(sys.argv[1:])

sic = SimpleIRCClient(args)
asyncio.run(sic.main())
