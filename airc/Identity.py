#	pyirclib - Python IRC client library with DCC and anonymization support
#	Copyright (C) 2016-2020 Johannes Bauer
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
import random
import pkgutil
import datetime
import json
from .RandomDist import RandomDist

class _NicknameGenerator(object):
	def __init__(self, dbfile = None):
		self._dbfile = dbfile
		self._content = None

	def _read_dbfile(self):
		if self._content is None:
			words = [ ]

			if self._dbfile is None:
				data = pkgutil.get_data("airc.data", "nicknames.txt")
				words = data.decode("ascii").split("\n")[:-1]
			else:
				with open(self._dbfile) as f:
					for line in f:
						words.append(line.rstrip("\r\n"))
			self._content = words

	@staticmethod
	def _invert(text):
		result = ""
		for char in text:
			if char.islower():
				result += char.upper()
			else:
				result += char.lower()
		return result

	@classmethod
	def _obfuscate(cls, text):
		if random.randint(0, 1) == 0:
			text = text.replace("e", "3")
		if random.randint(0, 1) == 0:
			text = text.replace("i", "1")
		if random.randint(0, 1) == 0:
			text = text.replace("a", "4")
		if random.randint(0, 3) == 0:
			text = cls._invert(text)
		return text

	@staticmethod
	def _fixup(text):
		replacements = {
			"0":	"O",
			"1":	"I",
			"2":	"Z",
			"3":	"E",
			"4":	"A",
			"5":	"S",
			"6":	"G",
			"7":	"T",
			"8":	"B",
			"9":	"g",
		}
		if text[0] in replacements:
			text = replacements[text[0]] + text[1:]
		return text

	def _rand_word(self):
		return self._obfuscate(random.choice(self._content))

	def _concat_rand_words(self, maxlen):
		name = ""
		for i in range(5):
			next_word = self._rand_word()
			if len(next_word) + len(name) > maxlen:
				break
			else:
				name += next_word
		return name

	def generate(self, maxlen = 8):
		self._read_dbfile()

		# Generate a nickname
		nick = self._concat_rand_words(maxlen = maxlen)

		# Append a number
		if len(nick) < maxlen:
			digits = maxlen - len(nick)
			if digits == 4:
				rnd_range = (1980, 2020)
			else:
				if digits > 2:
					digits = 2
				rnd_range = (1, (10 ** digits) - 1)
			rndval = random.randint(rnd_range[0], rnd_range[1])
			nick += str(rndval)

		# Remove leading numbers and such
		nick = self._fixup(nick)
		return nick

class BaseIdentity(object):
	def __init__(self, nickname, username = None, realname = None, version = None, timezone_hrs = None, clk_deviation_secs = 0):
		self._nickname = nickname
		self._username = username
		self._realname = realname
		if self._username is None:
			self._username = self._nickname
		if self._realname is None:
			self._realname = self._nickname
		self._version = version
		self._timezone_hrs = timezone_hrs
		self._clk_deviation_secs = clk_deviation_secs

	def nickname(self, permutation_index):
		if permutation_index == 0:
			return self._nickname
		else:
			return "%s%03d" % (permutation_index)

	@property
	def username(self):
		return self._nickname

	@property
	def realname(self):
		return self._nickname

	@property
	def version(self):
		return self._version

	@property
	def timezone_hrs(self):
		return self._timezone_hrs

	def now(self):
		if self.timezone_hrs is not None:
			now = datetime.datetime.utcnow() + datetime.timedelta(0, self._clk_deviation_secs + (3600 * self._timezone_hrs))
			return now.strftime("%a %b %H:%M:%S %Y")
		else:
			return None

	def __str__(self):
		data = [ self.nickname ]
		if self.version is not None:
			data.append("IRC client = \"%s\"" % (self.version))
		if self.timezone_hrs is not None:
			data.append("TZ %+d hrs" % (self.timezone_hrs))
		data = ", ".join(data)
		return "%s<%s>" % (self.__class__.__name__, data)

class FakeIdentity(BaseIdentity):
	def __init__(self):
		timezone_hrs = random.randint(-11, 12)
		clk_deviation_secs = random.randint(-30, 30)
		version = self._select_version()
		nickname = _NicknameGenerator().generate()
		BaseIdentity.__init__(self, nickname, version = version, timezone_hrs = timezone_hrs, clk_deviation_secs = clk_deviation_secs)

	def nickname(self, permutation_index):
		if permutation_index == 0:
			return self._nickname
		elif permutation_index == 1:
			return self._nickname + "^"
		elif permutation_index == 2:
			return self._nickname + "X"
		else:
			return self._nickname + "%3d" % (permutation_index)

	def _select_version(self):
		client_data = pkgutil.get_data("airc.data", "clients.json")
		client_data = json.loads(client_data)
		random_dist = RandomDist(client_data)
		return random_dist.event()


if __name__ == "__main__":
	for i in range(10):
		identity = FakeIdentity()
		print(identity, identity.now())

	identity = BaseIdentity("foobar", version = "myClient", timezone_hrs = 0)
	print(identity, identity.now())
