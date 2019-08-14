'''
TODO: Probably remove this file eventually.
'''
import os
import sys
import json
import hashlib
from cincoconfig import *

schema = Schema()
schema.hash = SecureField(action="hash_md5", default="herpderp")
schema.nodefault = SecureField(action="hash_md5")
schema.password = SecureField(action="enc_aes256", default="herpderp")
schema.xorpass = SecureField(action="enc_xor", default="herpderp")

config = schema()
config.nodefault = "nodefault"

if os.path.isfile("test.cfg.json"):
    print("Load")
    config.load("test.cfg.json", "json")

print("hash:", config.hash)
print("nodef:", config.nodefault)
print("password (should be cleartext):", config.password)
print("xor pass (should be cleartext):", config.xorpass)

if schema.hash.check_hash(config, "herpderp"):
    print("WE DID IT")

print("Save")
config.save("test.cfg.json", "json")
sys.exit(0)

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
