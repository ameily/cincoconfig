'''
TODO: Probably remove this file eventually.
'''
import os
import sys
import json
import hashlib
from cincoconfig import *

cfg = Schema()
cfg.hash = SecureField(action="hash_md5", default="herpderp")
cfg.password = SecureField(action="enc_aes256", default="herpderp")
cfg.server.host = StringField()
cfg.server.db.host = StringField(default="ferp")
cfg.server.db.ferp.blah.fah.bam = IntField(default=10)

config = cfg()

print("BAM: ", config.server.db.ferp.blah.fah.bam)
print("HOST: ", config.server.host)
print("DBHOST: ", config.server.db.host)

if os.path.isfile("test.cfg.json"):
    print("Load")
    config.load("test.cfg.json", "json")

print("hash:", config.hash)
print("password (should be cleartext):", config.password)

if config.hash == SecureField.hash("herpderp", "hash_md5"):
    print("WE DID IT")

print("Save")
config.save("test.cfg.json", "json")

print("Load")
config.load("test.cfg.json", "json")

print("hash:", config.hash)
print("password (should be cleartext):", config.password)

config.password = "password"
config.hash = "password"
print("Change hash:", config.hash)
print("Change password (should be cleartext):", config.password)

print("Save")
config.save("test.cfg.json", "json")

print("Load")
config.load("test.cfg.json", "json")

print("hash:", config.hash)
print("password (should be cleartext):", config.password)
