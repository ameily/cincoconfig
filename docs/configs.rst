configs
=======

.. autoclass:: cincoconfig.Schema
    :members:

    .. automethod:: _add_field
    .. automethod:: _get_field
    .. automethod:: __setattr__
    .. automethod:: __getattr__
    .. automethod:: __iter__
    .. automethod:: __call__


.. autoclass:: cincoconfig.Config
    :members:

    .. automethod:: _add_field
    .. automethod:: _get_field
    .. automethod:: __setattr__
    .. automethod:: __getattr__
    .. automethod:: __setitem__
    .. automethod:: __getitem__
    .. automethod:: __iter__


Internal Classes
----------------

The following base classes are used internally and should not be directly referenced.

.. autoclass:: cincoconfig.abc.BaseSchema
    :members:

    .. automethod:: _add_field
    .. automethod:: _get_field


.. autoclass:: cincoconfig.abc.BaseConfig
    :members:

    .. automethod:: _add_field
    .. automethod:: _get_field
    .. autoattribute:: _keyfile
    .. autoattribute:: _key_filename
