Recipes
=======

Validate Configuration On Load
------------------------------

When creating the configuration, by calling the :class:`~cincoconfig.Schema` object, you can pass in
a callback method that will be called whenever the configuration file is loaded from disk. The
callback accepts a single argument: the configuration.

.. code-block:: python

    def validate_config(config: Config) -> None:
        '''
        Validates that if both x and y are specified in the config that x is less than y.
        '''
        if config.x and config.y and config.x < config.y:
            raise ValueError('x must be < y')

    schema = Schema()
    schema.x = IntField()
    schema.y = IntField()

    config = schema(validator=validate_config)
    config.load('myconfig.json', format='json')


Allow Multiple Configuration Files
----------------------------------

The :class:`~cincoconfig.IncludeField` allows users to specify an additional file to parse when
loading the config from disk. The ``IncludeField`` is processes prior to setting parsing any
of the configuration values. So, the entire config file and any included config files are combined
in memory prior to parsing.

.. code-block:: python

    schema = Schema()
    schema.include = IncludeField()
    # other fields
    config = schema()

    config.load('mycfg.json', format='json')

**mycfg.json**

.. code-block:: json

    {
        "include": "otherfile.json"
    }

IncludeFields can occur anywhere in a configuration, however, when the included file is processed,
it is handled in the same scope as where the IncludeField was defined.


Dynamically Get and Set Configuration Values
--------------------------------------------

The :class:`~cincoconfig.Config` class supports getting and setting  config values via both direct
attribute access and the ``__getitem__`` and ``__setitem__`` protocols. The ``__getitem__`` and
``__setitem__`` methods have the added benefit of supporting getting and setting nested config
values.

.. code-block:: python

    schema = Schema()
    schema.x = IntField()
    schema.db.port = IntField(default=27017)
    schema.db.host = HostnameField(default='127.0.0.1', allow_ipv4=True)

    config = schema()
    config.load('mycfg.json', format='json')

    #
    # get the set port
    # equivalent to:
    #
    #     print(config.db.port)
    #
    print(config['db.port'])

    #
    # set the hostname
    # equivalent to:
    #
    #    config.db.host = 'db.example.com'
    #
    config['db.host'] = 'db.example.com'

Using ``__getitem__`` and ``__setitem__`` is useful in situations where you need dynamic
programmatic access to the configuration values, such as supporting a generic REST API to interact
with the configuration.


List Field of Complex Types
---------------------------

The :class:`~cincoconfig.ListField` performs value validation for each item by accepting either a
:class:`~cincoconfig.Field` or :class:`~cincoconfig.Schema`. Consider the example of a list of
webhooks.

.. code-block:: python

    webhook_schema = Schema()
    webhook_schema.url = UrlField(required=True)
    webhook_schema.verify_ssl = BoolField(default=True)

    schema = Schema()
    schema.issue_webhooks = ListField(webhook_schema)
    schema.merge_request_webhooks = ListField(webhook_schema)

    config = schema()

    wh = webhook_schema()
    wh.url = 'https://google.com'
    config.issue_webhooks.append(wh)

Here, the ``webhook`` schema is usable across mutliple configurations. As seen here, it is not
very intuative to create reusable configuration items. The Schema
:meth:`~cincoconfig.Schema.make_type` method is designed to make working with these reusable
configurations easier. ``make_type`` creates a new type, inheriting from
:class:`~cincoconfig.Config` that is more Pythonic.

.. code-block:: python

    webhook_schema = Schema()
    webhook_schema.url = UrlField(required=True)
    webhook_schema.verify_ssl = BoolField(default=True)

    schema = Schema()
    schema.issue_webhooks = ListField(webhook_schema)
    schema.merge_request_webhooks = ListField(webhook_schema)

    config = schema()

    wh = WebHook(url='https://google.com')
    config.issue_webhooks.append(wh)
