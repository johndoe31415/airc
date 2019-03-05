#!/usr/bin/python3
import collections
import json

def plausible(client):
	lwr = client.lower()
	return any(pattern in lwr for pattern in [ "xchat", "hexchat", "mirc", "rcirc", "irssi", "icechat", "thunderbird", "colloquy", "znc", "weechat", "thelounge", "textual", "kvirc", "quassel", "adiirc", "konversat", "limechat" ])

with open("versions.json") as f:
	versions = json.load(f)
clients = [ client for client in versions.values() if plausible(client) ]
rejects = [ client for client in versions.values() if not plausible(client) ]

for reject in sorted(set(rejects)):
	print(reject)

ctr = collections.Counter(clients)
with open("clients.json", "w") as f:
	json.dump(ctr, f)
#for (name, counts) in ctr.most_common():
#	print("%-120s %d" % (name[:119], counts))


