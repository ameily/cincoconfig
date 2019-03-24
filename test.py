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

config = cfg()

if os.path.isfile("test.cfg.json"):
    print("Load")
    config.load("test.cfg.json", "json")

print("hash:", config.hash)
print("password (should be cleartext):", config.password)

if cfg.hash.check_hash(config, "herpderp"):
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
