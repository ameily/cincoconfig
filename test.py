'''
TODO: Probably remove this file eventually.
'''
import json
from cincoconfig import *

cfg = Schema()
cfg.mode = StringField(required=True, choices=('development', 'production'), default='production')
cfg.server.port = PortField(required=True, default=8080)
cfg.server.host = HostnameField(required=True, default='localhost')
cfg.server.ssl = BoolField(default=False)

cfg.database.host = HostnameField(required=True, default='localhost')
cfg.database.user = StringField(required=False)
cfg.database.password = StringField(required=False)

config = cfg()

print(cfg.to_json())

print()

print(config._to_tree())

print()
try:
    config.mode = 'ferp'
except ValueError as e:
    print('failed to set config:', str(e))


config.server.port = 443
print('server port:', config.server.port)

try:
    config.server.port = 100000
except ValueError as e:
    print('failed to set config:', str(e))
