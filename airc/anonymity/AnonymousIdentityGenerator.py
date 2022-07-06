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

import pkgutil
import json
import random
import string
import datetime
from airc.IRCIdentity import IRCIdentity
from airc.IRCIdentityGenerator import IRCIdentityGenerator
from airc.IRCIdentityGenerator import IRCIdentityGenerator
from .RandomDist import RandomDist

class AnonymousIdentityGenerator(IRCIdentityGenerator):
	_CLIENTS = None
	_REALNAMES_MALE = None
	_REALNAMES_FEMALE = None
	_USERNAMES = None

	@classmethod
	def _apply_text_mangle(cls, intext, mangler, percentage_chance):
		if random.randint(0, 99) < percentage_chance:
			return mangler(intext)
		else:
			return intext

	@classmethod
	def _alternating_case(cls, text):
		result = [ ]
		toupper = bool(random.randint(0, 1))
		for letter in text:
			if toupper:
				result.append(letter.upper())
			else:
				result.append(letter.lower())
			toupper = not toupper
		return "".join(result)

	@classmethod
	def _randomize_case(cls, text):
		result = [ ]
		for letter in text:
			toupper = bool(random.randint(0, 1))
			if toupper:
				result.append(letter.upper())
			else:
				result.append(letter.lower())
		return "".join(result)

	@classmethod
	def random_nickname(cls):
		if cls._USERNAMES is None:
			cls._USERNAMES = pkgutil.get_data("airc.anonymity.data", "usernames.txt").strip(b"\n").decode("utf-8").split("\n")
		basis = random.choice(cls._USERNAMES)
		basis = cls._apply_text_mangle(basis, lambda text: text.upper(), 25)
		basis = cls._apply_text_mangle(basis, cls._alternating_case, 40)
		basis = cls._apply_text_mangle(basis, cls._randomize_case, 40)
		basis = cls._apply_text_mangle(basis, lambda text: text.replace("i", "1"), 25)
		basis = cls._apply_text_mangle(basis, lambda text: text.replace("e", "3"), 25)
		basis = cls._apply_text_mangle(basis, lambda text: text.replace("a", "4"), 25)
		basis = cls._apply_text_mangle(basis, lambda text: text.replace("ck", "x"), 25)
		basis = cls._apply_text_mangle(basis, lambda text: text.replace("o", "0"), 25)
		match RandomDist({
			"nothing":			3,
			"twodig":			1,
			"year":				1,
		}).event():
			case "twodig":
				basis += str(random.randint(1, 99))
			case "year":
				min_age = 18
				max_age = 55
				year = datetime.datetime.today().year
				min_year = year - max_age
				max_year = year - min_age
				basis += str(random.randint(min_year, max_year))
		basis = cls._apply_text_mangle(basis, lambda text: text + random.choice("^_"), 25)
		basis = cls._apply_text_mangle(basis, lambda text: random.choice("^_") + text, 25)
		return basis

	@classmethod
	def random_username_realname(cls):
		if cls._REALNAMES_MALE is None:
			cls._REALNAMES_MALE = pkgutil.get_data("airc.anonymity.data", "realnames_male.txt").strip(b"\n").decode("utf-8").split("\n")
			cls._REALNAMES_FEMALE = pkgutil.get_data("airc.anonymity.data", "realnames_female.txt").strip(b"\n").decode("utf-8").split("\n")

		match RandomDist({
			"male":		3,
			"female":	1,
		}).event():
			case "male":
				realname = random.choice(cls._REALNAMES_MALE)
			case "female":
				realname = random.choice(cls._REALNAMES_FEMALE)

		name = realname.lower()
		match RandomDist({
			"only_name":	10,
			"with_suffix":	3,
		}).event():
			case "only_name":
				username = name
			case "with_suffix":
				username = name + random.choice(string.ascii_lowercase)
		return (username, realname)

	@classmethod
	def random_client(cls):
		if cls._CLIENTS is None:
			cls._CLIENTS = RandomDist(json.loads(pkgutil.get_data("airc.anonymity.data", "client_versions.json")))
		match RandomDist({
			"have_client":	50,
			"no_client":	50
		}).event():
			case "have_client":
				return cls._CLIENTS.event()
			case "no_client":
				return None

	def _generate(self):
		timezone_hrs = random.randint(-12, 12)
		clk_deviation_secs = random.randint(-300, 300)
		(username, realname) = self.random_username_realname()
		return IRCIdentity(nickname = self.random_nickname(), username = username, realname = realname, version = self.random_client(), timezone_hrs = timezone_hrs, clk_deviation_secs = clk_deviation_secs)

	def __iter__(self):
		while True:
			yield self._generate()
