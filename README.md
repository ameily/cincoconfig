# Cinco Config

[![Build Status](https://travis-ci.org/ameily/cincoconfig.svg?branch=master)](https://travis-ci.org/ameily/cincoconfig)
[![Coverage Status](https://coveralls.io/repos/github/ameily/cincoconfig/badge.svg?branch=master)](https://coveralls.io/github/ameily/cincoconfig?branch=master)

Next generation universal configuration file parser. The config file structure is defined
programmatically and expressively, no need to create classes and inheritance.

Let's get right to it:

```python
# app_config.py
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
schema.db.user = StringField()

# some configuration values are sensitive, such as credentials, so
# cincoconfig provides config value encryption when the value is
# saved to disk via the SecureField
schema.db.password = SecureField()


# once a schema is defined, build the actual configuration object
# that can load config files from disk and interact with the values
config = schema()

# print the set http port
print(config.http.port) # >>> 8080

# set a config value manually
if config.mode == 'production':
    config.db.name = config.db.name + '_production'

print(config.dumps(format='json', pretty=True))
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
#     "name": "my_app_production"
#   }
# }
```
