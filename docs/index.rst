.. cincoconfig documentation master file, created by
   sphinx on Sun Mar 17 21:57:06 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to cincoconfig's documentation!
=======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   recipes
   configs
   fields
   formats
   encryption
   stubs
   support




``cincoconfig`` is an easy to use configuration file management library. It allows you to build
custom application and library configurations declaratively without any subclassing or
specializations. Cincoconfig ships with 20+ builtin :doc:`fields` with comprehensive value
validation.

cincoconfig has no hard dependencies, however, several features become available by
installing several dependencies, including (see `requirements/requirements-features.txt` for full
list):

 - Configuration value encryption (:class:`~cincoconfig.SecureField`) - requires ``cryptography``
 - YAML config file support - requires ``PyYaml``
 - BSON config file support - requires ``bson``

Configuration values are directly accessed as attributes.

.. code-block:: python

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
    schema.http.ssl.ca_file = FilenameField()
    schema.http.ssl.key_file = FilenameField()
    schema.http.ssl.cert_file = FilenameField()

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


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
