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

import ssl

class IRCServer():
	def __init__(self, hostname: str, port: int = 6666, use_ssl: bool = False, tls_insecure: bool = False, password: str | None = None):
		self._hostname = hostname
		self._port = port
		self._password = password
		self._use_ssl = use_ssl
		self._tls_insecure = tls_insecure

	@property
	def hostname(self):
		return self._hostname

	@property
	def port(self):
		return self._port

	@property
	def use_ssl(self):
		return self._use_ssl

	@property
	def tls_insecure(self):
		return self._tls_insecure

	@property
	def password(self):
		return self._password

	@property
	def ssl_ctx(self):
		if self._use_ssl is False:
			return None
		else:
			ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
			if not self._tls_insecure:
				ssl_ctx.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
				ssl_ctx.load_verify_locations(capath = "/etc/ssl/certs")
				ssl_ctx.check_hostname = True
				ssl_ctx.set_ciphers("!NULL:!EXP:!LOW:!MEDIUM:!ADH:!AECDH:!IDEA:!SEED:!MD5:!RC4:!DES:!DSS:!CAMELLIA:!AESCCM8:HIGH+EECDH:HIGH+EDH:!SHA:+SHA256:+RSA:+AES:+DHE:+ARIA")
			else:
				ssl_ctx.verify_mode = ssl.CERT_NONE
				ssl_ctx.check_hostname = False

			return ssl_ctx

	def __str__(self):
		strs = [ f"{self.hostname}:{self.port}" ]
		if self.use_ssl:
			strs.append("SSL")
		if self.password is not None:
			strs.append("PASSWD")
		strs = " ".join(strs)
		return f"IRCServer<{strs}>"
