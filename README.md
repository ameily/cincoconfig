# Cinco Config

[![Build Status](https://travis-ci.org/ameily/cincoconfig.svg?branch=master)](https://travis-ci.org/ameily/cincoconfig)
[![Coverage Status](https://coveralls.io/repos/github/ameily/cincoconfig/badge.svg?branch=master)](https://coveralls.io/github/ameily/cincoconfig?branch=master)
[![Docs Status](https://readthedocs.org/projects/cincoconfig/badge/)](https://cincoconfig.readthedocs.io/en/latest/)

Next generation universal configuration file parser. The config file structure is defined
programmatically and expressively, no need to create classes and inheritance.

Let's get right to it:

```python
# app_config.py
import getpass
from cincoconfig import *

# first, define the configuration's schema -- the fields available that
# customize the application's or library's behavior
schema = Schema()
schema.mode = ApplicationModeField(default='production')

# nested configurations are built on the fly
# http is now a subconfig
schema.http.port = PortField(default=8080, required=True)

# each field has its own validation rules that are run anytime the config
# value is loaded from disk or modified by the user.
# here, this field only accepts IPv4 network addresses and the user is
# required to define this field in the configuration file.
schema.http.address = IPv4AddressField(default='127.0.0.1', required=True)

schema.http.ssl.enabled = BoolField(default=False)
schema.http.ssl.cafile = FilenameField()
schema.http.ssl.keyfile = FilenameField()
schema.http.ssl.certfile = FilenameField()

schema.db.host = HostnameField(allow_ipv4=True, required=True, default='localhost')
schema.db.port = PortField(default=27017, required=True)
schema.db.name = StringField(default='my_app', required=True)
schema.db.user = StringField(default='admin')

# some configuration values are sensitive, such as credentials, so
# cincoconfig provides config value encryption when the value is
# saved to disk via the SecureField
schema.db.password = SecureField()

# get a field programmatically
print(schema['db.host']) # >>> schema.db.host

# once a schema is defined, build the actual configuration object
# that can load config files from disk and interact with the values
config = schema()

# print the http port
print(config.http.port) # >>> 8080

# print the http port programmatically
print(config['http.port']) # >>> 8080

config.db.password = getpass.getpass("Enter Password: ") # < 'password'

# set a config value manually
if config.mode == 'production':
    config.db.name = config.db.name + '_production'

print(config.dumps(format='json', pretty=True).decode())
# {
#   "mode": "production",
#   "http": {
#     "port": 8080,
#     "address": "127.0.0.1"
#     "ssl": {
#       "enabled": false
#     }
#   },
#   "db": {
#     "host": "localhost",
#     "port": 27017,
#     "name": "my_app_production",
#     "user": "admin",
#     "password": {
#       "method": "best",
#       "ciphertext": "<ciphertext>"
#     }
#   }
# }
```

### Override Configuration with Command Line Arguments (argparse)

```python
# config.py
schema = Schema()
schema.mode = ApplicationModeField(default='production', modes=['production', 'debug'])
schema.http.port = PortField(default=8080, required=True)
schema.http.address = IPv4AddressField(default='127.0.0.1', required=True)

config = schema()

# __main__.py
import argparse
from .config import config

parser = argparse.ArgumentParser()

parser.add_argument('-H', '--host', action='store', dest='http.address')
parser.add_argument('-p', '--port', action='store', type=int, dest='http.port')
parser.add_argument('-d', '--debug', action='store_const', const='debug', dest='mode')
parser.add_argument('-c', '--config', action='store')

args = parser.parse_args()
if args.config:
    config.load(args.config, format='json')

config.cmdline_args_override(args, ignore=['config'])
```
