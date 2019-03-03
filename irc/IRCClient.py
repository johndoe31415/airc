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

import re
import ssl
import socket
import threading
import collections
import logging

_log = logging.getLogger("irc.IRCClient")

class _ReadingThread(threading.Thread):
	def __init__(self, socket, callback):
		threading.Thread.__init__(self)
		self._active = True
		self._socket = socket
		self._callback = callback
		self._buffer = bytearray()

	def run(self):
		while self._active:
			data = self._socket.recv(4096)
			if len(data) == 0:
				# Connection interrupted
				break
			self._buffer += data
			splitbuf = self._buffer.split(b"\r\n")
			self._buffer = splitbuf[-1]
			for rxmsg in splitbuf[:-1]:
				self._callback(rxmsg.decode("utf-8"))

	def quit(self):
		self._active = False

ChannelMsg = collections.namedtuple("ChannelMsg", [ "channel", "origin", "text" ])
PrivMsg = collections.namedtuple("PrivMsg", [ "origin", "text" ])
Origin = collections.namedtuple("Origin", [ "nick", "alias", "server" ])

class IRCClient(object):
	_RX_MSGS = {
		"privmsg":	re.compile("^:(?P<from>[^ ]+) PRIVMSG (?P<to>[^ ]+) :(?P<text>.*)$"),
		"rawcmd":	re.compile("^:(?P<host>[^ ]+) (?P<code>\d{3}) (?P<msg>.*)$"),
		"ping":		re.compile("^PING (?P<text>.*)$"),
	}
	_RE_ORIGIN = re.compile("^(?P<nick>[^!]+)!(?P<alias>[^@]+)@(?P<server>.*)$")
	_TIMER_INTERVAL = 30
	_NO_RX_THRESHOLD = 6

	def __init__(self, server, username, port = 6667, password = None, usessl = False):
		_log.debug("Connecting to %s:%d using ssl %s" % (server, port, str(usessl)))
		self._channellisteners = { }
		self._privmsglisteners = [ ]
		self._socket = socket.create_connection((server, port))
		_log.info("Connected successfully to %s:%d" % (server, port))
		if usessl:
			self._socket = ssl.wrap_socket(self._socket)
			_log.debug("SSL wrapper active")
		self._readthread = _ReadingThread(self._socket, self.receivedata)
		self._readthread.start()
		self._tickthread = threading.Timer(self._TIMER_INTERVAL, self._tickcallback)
		self._tickthread.start()
		self._no_rx_count = 0
		self._connected = True
		if password is not None:
			_log.debug("Sending server password")
			self.transmitcmd("PASS %s" % (password))
		self.transmitcmd("NICK %s" % (username))
		self.transmitcmd("USER %s %s %s :%s" % (username, username, username, username))

	@property
	def connected(self):
		return self._connected

	@staticmethod
	def parse_origin(originstr):
		result = IRCClient._RE_ORIGIN.match(originstr)
		if result:
			return Origin(**result.groupdict())

	def _tickcallback(self):
		self._no_rx_count += 1
		if (self._no_rx_count >= self._NO_RX_THRESHOLD) and self.connected:
			_log.error("Connection timed out, shutting down and closing socket")
			self._connected = False
			self._readthread.quit()
			try:
				self._socket.shutdown(socket.SHUT_RDWR)
			except socket.error:
				pass
		else:
			self._tickthread = threading.Timer(self._TIMER_INTERVAL, self._tickcallback)
			self._tickthread.start()

	def listenchannel(self, channel, callback):
		self._channellisteners[channel] = callback

	def listenprivmsg(self, callback):
		self._privmsglisteners.append(callback)

	def _rxchannel(self, chanmsg):
		listener = self._channellisteners.get(chanmsg.channel)
		if listener is not None:
			listener(chanmsg)

	def _rxmsg(self, privmsg):
		for listener in self._privmsglisteners:
			listener(privmsg)

	def receivecmd(self, msgtype, params):
		_log.debug("  <- %s: %s" % (str(msgtype), str(params)))
		if msgtype == "privmsg":
			if params["to"].startswith("#"):
				# Incoming channel message
				chanmsg = ChannelMsg(channel = params["to"], origin = self.parse_origin(params["from"]), text = params["text"])
				self._rxchannel(chanmsg)
			else:
				self._rxmsg(PrivMsg(origin = self.parse_origin(params["from"]), text = params["text"]))
		elif msgtype == "rawcmd":
			code = int(params["code"])
		elif msgtype == "ping":
			self.transmitcmd("PONG %s" % (params["text"]))

	def receivedata(self, data):
		if not self.connected:
			return

		self._no_rx_count = 0
		for (msgtype, regex) in self._RX_MSGS.items():
			result = regex.match(data)
			if result is not None:
				result = result.groupdict()
				self.receivecmd(msgtype, result)
				break
		else:
			_log.debug("? <- '%s'" % (data))

	def msg(self, recipient, text):
		self.transmitcmd("PRIVMSG %s :%s" % (recipient, text))

	def join(self, channel):
		assert(channel.startswith("#"))
		self.transmitcmd("JOIN %s" % (channel))

	def sendtochannel(self, channel, msg):
		assert(channel.startswith("#"))
		self.transmitcmd("PRIVMSG %s :%s" % (channel, msg))

	def transmitcmd(self, cmd):
		if not self.connected:
			return
		_log.debug("  -> %s" % (str(cmd)))
		self._socket.send((cmd + "\r\n").encode("utf-8"))

