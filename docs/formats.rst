formats
=======


.. autoclass:: cincoconfig.FormatRegistry
    :members:


Available Formats
-----------------

The following formats are included within cincoconfig. There should not be a reason to directly
reference these classes. Instead, to save or load a configuration in the JSON format, for example,
use:

.. code-block:: python

    config.save('config.json', format='json')

This will automatically create the :class:`cincoconfig.formats.json.JsonConfigFormat`.
