'''
TODO: Probably remove this file eventually.
'''
import os
import sys
import json
import hashlib
from cincoconfig import *

cfg = Schema()
cfg.hash = SecureStringField(action="hash_md5", default="hackme4fun")
cfg.password = SecureStringField(action="enc_aes256", default="hackme4fun")

config = cfg()

if os.path.isfile("test.cfg.json"):
    print("Load")
    config.load("test.cfg.json", "json")

print("hash:", config.hash)
print("password (should be cleartext):", config.password)

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
