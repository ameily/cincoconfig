'''
TODO: Probably remove this file eventually.
'''
import json
from cincoconfig import *

cfg = Config()
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
print(config.to_json())
