'''
TODO: Probably remove this file eventually.
'''
import json
from cincoconfig.config import Config, ConfigGroup

cfg = Config()
cfg.mode = "development"
cfg.server.port = 8080
cfg.server.host = "localhost"
cfg.server.ssl = False

cfg.database.host = "localhost"
cfg.database.user = "user"
cfg.database.opts = ["1", "2", "3"]

cfg.database.ferp = ConfigGroup()
cfg.database.ferp.derp = "blah"
cfg.database.ferp.herp.merp = "doubleblah"

print(json.dumps(cfg.to_json(), indent=4, sort_keys=True))
