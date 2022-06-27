#!/usr/bin/python3
import os
import airc
import asyncio

async def main():
	irc_servers = [ airc.IRCServer(hostname = "irc.freenode.org") ]
	identity = airc.IRCIdentity(nickname = "x" + os.urandom(4).hex())
	idgen = airc.ListIRCIdentityGenerator([ identity ])
	sess = airc.IRCSession(irc_client_class = airc.BasicIRCClient, irc_servers = irc_servers, identity_generator = idgen)
	print("SESS")

	task = sess.task()
	print("TASK")
	await task
	print("TASK done")

asyncio.run(main())
