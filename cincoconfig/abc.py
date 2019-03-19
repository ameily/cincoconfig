#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Abstract base classes.
'''

from typing import Any, Callable, Union
from . import config


class Field:
    '''
    The base configuration field. Fields provide validation and the mechanisms to retrieve and set
    values from a :class:`Config`. Field's are composable and reusable so they should not store
    state or store the field value.

    Validation errors should raise a :class:`ValueError` exception with a brief message.

    There are three steps to validating a value:

    1. :meth:`validate` - checks the value against the *required* parameter and then calls:
    2. :meth:`_validate` - validate function that is implemented in subclasses of ``Field``
    3. ``Field.validator`` - custom validator method specified when the field is created

    The pseudo code for the :meth:`validate` function:

    .. code-block:: python
        :linenos:

        def validate(self, cfg, value):
            if value is None and self.required:
                raise ValueError

            value = self._validate(cfg, value)
            if self.validator:
                value = self.validate(cfg, value)
            return value

    Since each function in the validation chain returns the value, each validator can transform
    the value. For example, the :class:`BoolField` ``_validate`` method converts the string value
    to a :class:`bool`.

    Each Field has the following lifecycle:

    1. ``__init__`` - created by the application
    2. :meth:`__setkey__` - the field is added to a :class:`Schema`
    3. :meth:`__setdefault__` - the field is added to a config and the config is populated with the
        default value

    Whenever a config value is set, the following methods are called in this order:

    1. :meth:`validate` / :meth:`_validate` / ``validator`` - validation chain
    2. :meth:`__setval__` - set a validated value to the config

    Finally, whenever code retrieves a config value, the :meth:`__getval__` is called.

    Most field subclasses only need to implement the ``_validate`` method and most do not need to
    implement the ``__setkey__``, ``__setdefault__``, ``__getval__`` and ``__setval__`` methods,
    unless the field needs to modify the default behavior of these methods.

    The Field ``key`` is used to set and reference the value in the config.
    '''

    def __init__(self, *, name: str = None, key: str = None, required: bool = False,
                 default: Union[Callable, Any] = None,
                 validator: Callable[['config.Config', Any], Any] = None):
        '''
        :param name: field friendly name, used for error messages and documentation
        :param key: the key of the field in the config, this is typically not specified and,
            instead the :meth:`__setkey__` will be called by the config
        :param required: the field is required and a :class:`ValueError` will be raised if the
            value is ``None``
        :param default: the default value, which can be a called that is invoke with no arguments
            and should return the default value
        :param validator: an additional validator function that is invoked during validation
        '''
        self._name = name or None
        self.key = key or None
        self.required = required
        self._default = default
        self.validator = validator

    @property
    def default(self) -> Any:
        '''
        :returns: the field's default value
        '''
        return self._default() if callable(self._default) else self._default

    @property
    def name(self):
        '''
        :returns: the field's friendly name: ``name or key``
        '''
        return self._name or self.key

    def _validate(self, cfg: 'config.Config', value: Any) -> Any:
        '''
        Subclass validation hook. The default implementation just returns ``value`` unchanged.
        '''
        return value

    def validate(self, cfg: 'config.Config', value: Any) -> Any:
        '''
        Start the validation chain and verify that the value is specified if *required=True*.

        :param cfg: current config
        :param value: value to validate
        :returns: the validated value
        '''
        if self.required and value is None:
            raise ValueError('%s is required' % self.name)

        if value is None:
            return value

        value = self._validate(cfg, value)
        if self.validator:
            value = self.validator(cfg, value)

        return value

    def __setval__(self, cfg: 'config.Config', value: Any):
        '''
        Set the validated value in the config. The default implementation passes the value through
        the validation chain and then set's the validated value int he config.

        :param cfg: current config
        :param value: value to validated
        '''
        cfg._data[self.key] = self.validate(cfg, value)

    def __getval__(self, cfg: 'config.Config') -> Any:
        '''
        Retrieve the value from the config. The default implementation retrieves the value from the
        config by the field *key*.

        :param cfg: current config
        :returns: the value stored in the config
        '''
        return cfg._data[self.key]

    def __setkey__(self, schema: 'config.Schema', key: str):
        '''
        Set the field's *key*, which is called when the field is added to a schema. The default
        implementation just sets ``self.key = key``

        :param schema: the schema the field belongs to
        :param key: the field's unique key
        '''
        self.key = key

    def __setdefault__(self, cfg: 'config.Config'):
        '''
        Set the default value of the field in the config. This is called when the config is first
        created.

        :param cfg: current config
        '''
        cfg._data[self.key] = self.default

    def to_python(self, cfg: 'config.Config', value: Any) -> Any:
        '''
        Convert the basic value to a Python value. Basic values are serializable (ie. not complex
        types). The following must hold true for config file saving and loading to work:

        .. code-block:: python

            assert field.to_python(field.to_basic(value)) == value

        The default implementation just returns ``value``. This method is called when the config is
        saved to a file and will only be called with the value associated with this field.

        In general, basic types are any types that can be represented in JSON: string, number,
        list, dict, boolean.

        :param cfg: current config
        :param value: value to convert to a basic type
        :returns: the converted basic type
        '''
        return value

    def to_basic(self, cfg: 'config.Config', value: Any) -> Any:
        '''
        Convert the Python value to the basic value.

        The default implementation just returns ``value``. This method is called when the config is
        saved to a file and will only be called with the value associated with this field.

        :param cfg: current config
        :param value: value to convert to a Python type
        :returns: the converted Python type
        '''
        return value


class AnyField(Field):
    '''
    A field that accepts any value and does not perform any validation beyond the base Field's
    *required* check.
    '''


class ConfigFormat:
    pass
