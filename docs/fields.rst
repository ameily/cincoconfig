fields
======

.. autoclass:: cincoconfig.Field
    :members:

    .. automethod:: _validate
    .. automethod:: __setkey__
    .. automethod:: __setdefault__
    .. automethod:: __getval__
    .. automethod:: __setval__

.. autoclass:: cincoconfig.StringField
    :members:

.. autoclass:: cincoconfig.LogLevelField
    :members:

.. autoclass:: cincoconfig.ApplicationModeField
    :members:

.. autoclass:: cincoconfig.SecureField
    :members:

.. autoclass:: cincoconfig.IntField
    :members:

.. autoclass:: cincoconfig.FloatField
    :members:


.. autoclass:: cincoconfig.PortField
    :members:

.. autoclass:: cincoconfig.IPv4AddressField
    :members:

.. autoclass:: cincoconfig.IPv4NetworkField
    :members:

.. autoclass:: cincoconfig.HostnameField
    :members:

.. autoclass:: cincoconfig.FilenameField
    :members:

.. autoclass:: cincoconfig.BoolField
    :members:

.. autoclass:: cincoconfig.FeatureFlagField
    :members:

.. autoclass:: cincoconfig.UrlField
    :members:

.. autoclass:: cincoconfig.ListField
    :members:

.. autoclass:: cincoconfig.VirtualField
    :members:

.. autoclass:: cincoconfig.DictField
    :members:

.. autoclass:: cincoconfig.BytesField
    :members:

.. autoclass:: cincoconfig.IncludeField
    :members:


Secure Fields
-------------

The following fields provide secure configuration option storage and challenges.

.. autoclass:: cincoconfig.ChallengeField
    :members:

.. autoclass:: cincoconfig.DigestValue
    :members:

.. autoclass:: cincoconfig.SecureField
    :members:


Instance Method Field
---------------------

.. autofunction:: cincoconfig.instance_method


Internal Types and Base fields
------------------------------

The following classes are used internally by cincoconfig and should not have to be used or
referenced directly in applications. These are not included in the public API and must be imported
explicitly from the ``cincoconfig.fields`` module.

.. autoclass:: cincoconfig.DictProxy
    :members:

.. autoclass:: cincoconfig.ListProxy
    :members:

.. autoclass:: cincoconfig.NumberField
    :members:
