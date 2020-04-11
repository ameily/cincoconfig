stubs
=====

Cincoconfig configuration objects are dynamic in nature which makes working with a cincoconfig
object cumbersome inside of an IDE that attempts to provide autocomplete / Intellisense results.
To work around this, Python type stub files, ``*.pyi``, can be used that define the structure of a
cincoconfig configuration so that the IDE or type checker can work properly with configuration
objects.


.. autofunction:: cincoconfig.generate_stub
