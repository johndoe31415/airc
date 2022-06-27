#!/usr/bin/python3
import os
import airc
import asyncio
import logging

def setup_logging():
	loglevel = logging.EAVESDROP
	logging.basicConfig(format = "{name:>40s} [{levelname:.1s}]: {message}", style = "{", level = loglevel)

async def main():
#	irc_servers = [ airc.IRCServer(hostname = "irc.freenode.org") ]
	irc_servers = [ airc.IRCServer(hostname = "irc.freenode.org", port = 6697, use_ssl = True) ]
	identity = airc.IRCIdentity(nickname = "x" + os.urandom(4).hex())
	idgen = airc.ListIRCIdentityGenerator([ airc.IRCIdentity(nickname = "neo"), identity ])
	sess = airc.IRCSession(irc_client_class = airc.BasicIRCClient, irc_servers = irc_servers, identity_generator = idgen)
	task = sess.task()
	await task

setup_logging()
asyncio.run(main())
