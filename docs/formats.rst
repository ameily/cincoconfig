formats
=======

The following formats are included within cincoconfig. There should not be a reason to directly
reference these classes. Instead, to save or load a configuration in the JSON format, for example,
use:

.. code-block:: python

    config.save('config.json', format='json')

This will automatically create the :class:`cincoconfig.formats.json.JsonConfigFormat`.

.. autoclass:: cincoconfig.formats.BsonConfigFormat
    :members:

.. autoclass:: cincoconfig.formats.JsonConfigFormat
    :members:

.. autoclass:: cincoconfig.formats.PickleConfigFormat
    :members:

.. autoclass:: cincoconfig.formats.XmlConfigFormat
    :members:

    .. automethod:: _to_element
    .. automethod:: _from_element
    .. automethod:: _prettify

.. autoclass:: cincoconfig.formats.YamlConfigFormat
    :members:


Base Classes
------------

All configuration file formats must inherit from and implement all abstract methods in the
:class:`cincoconfig.abc.ConfigFormat` class.

.. autoclass:: cincoconfig.ConfigFormat
    :members:
