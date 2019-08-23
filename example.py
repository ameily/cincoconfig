'''
Working example usage based on README.md. No python deps required. Just run it.
'''
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
schema.db.user = StringField()

# some configuration values are sensitive, such as credentials, so
# cincoconfig provides config value encryption when the value is
# saved to disk via the SecureField
schema.db.password = SecureField()

# some configuration values are sensitive and do not need to be
# stored in the clear. For example, for a user's application access
# password. For this, cincoconfig provides ChallengeField where the
# value is securely stored as a hash
schema.app.admin_password = ChallengeField()

# once a schema is defined, build the actual configuration object
# that can load config files from disk and interact with the values
config = schema()

# print the set http port
print("Port:", config.http.port)

# set a config value manually
if config.mode == 'production':
    config.db.name = config.db.name + '_production'

config.db.user = "admin"
config.db.password = "mydbpassword"

config.app.admin_password = getpass.getpass("Create your application access password: ")

# value is secure at runtime and when written to disk.
# The clear-text data is never stored for a challenge field.
print("Admin password hash: ", config.app.admin_password)

# Check a user's input against a ChallengeField
try:
    config.app.admin_password.challenge(getpass.getpass("Enter the same password to test: "))
except ValueError:
    print("That password didn't match! Access denied!")
else:
    print("Password match! Challenge passed.")

print("Full config:")
print(config.dumps(format='json', pretty=True).decode())
