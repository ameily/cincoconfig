# Cinco Config

[![Build Status](https://travis-ci.org/ameily/cincoconfig.svg?branch=master)](https://travis-ci.org/ameily/cincoconfig)
[![Coverage Status](https://coveralls.io/repos/github/ameily/cincoconfig/badge.svg?branch=master)](https://coveralls.io/github/ameily/cincoconfig?branch=master)

Next generation universal configuration file parser. The config file structure is defined
programmatically and expressively, no need to create classes and inheritance.

Let's get right to it:

```python
# app_config.py
from cincoconfig import *

schema = Schema()
schema.mode = ApplicationModeField(default='production')

schema.http.port = PortField(default=8080, required=True)
schema.http.address = IPv4AddressField(default='127.0.0.1', required=True)

schema.http.ssl.enabled = BoolField(default=False)
schema.http.ssl.cafile = FilenameField()
schema.http.ssl.keyfile = FilenameField()
schema.http.ssl.certfile = FilenameField()

schema.db.host = HostnameField(allow_ipv4=True, required=True, default='localhost')
schema.db.port = PortField(default=27017, required=True)
schema.db.name = StringField(default='my_app', required=True)

config = schema()

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
#     "name": "my_app"
#   }
# }
```
