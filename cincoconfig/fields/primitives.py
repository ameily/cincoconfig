#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from typing import Union, Any, Iterator, Callable
from cincoconfig.abc import Field, AnyField
from cincoconfig.config import Config


__all__ = ('BoolField', 'ListField', 'DictField', 'ListProxy', 'VirtualField')


class ListProxy:
    '''
    A Field-validated :class:`list` proxy. This proxy supports all methods that the builtin
    ``list`` supports with the added ability to validate items against a :class:`Field`. This is
    the field returned by the :class:`ListField` validation chain.
    '''

    def __init__(self, cfg: Config, field: Field, items: list = None):
        '''
        :param cfg: current config
        :param field: field to validate against
        :param items: initial list items
        '''
        self.cfg = cfg
        self.field = field
        self._items = []

        if items:
            for item in items:
                self.append(item)

    def __len__(self) -> int:
        return len(self._items)

    def __eq__(self, other: Union[list, 'ListProxy']) -> bool:
        '''
        :returns: this list content is equal to other list content
        '''
        if isinstance(other, ListProxy):
            other = other._items
        return self._items == other

    def __iter__(self) -> Iterator:
        '''
        :returns: iterator over items
        '''
        return iter(self._items)

    def append(self, item: Any):
        '''
        Validate a new item and then append it to the list if validation succeededs.
        '''
        value = self.field.validate(self.cfg, item)
        self._items.append(value)

    def __add__(self, other: Union[list, 'ListProxy']) -> 'ListProxy':
        '''
        Create a new ListProxy containing items from this list and another list.

        :param other: other list to combine
        :returns: new ListProxy that targets the same ``cfg`` and the same ``field`` with a
            concatenation of items from this list and ``other``
        '''
        if isinstance(other, ListProxy):
            other = other._items

        return ListProxy(self.cfg, self.field, self._items + other)

    def __iadd__(self, other: Union[list, 'ListProxy']) -> 'ListProxy':
        '''
        Extend list by appending elements from the iterable.

        :param other: other list
        :returns: ``self``
        '''
        self.extend(other)
        return self

    def __getitem__(self, index: int):
        return self._items[index]

    def __delitem__(self, index: int):
        del self._items[index]

    def __setitem__(self, index: int, value: Any):
        self._items[index] = self.field.validate(self.cfg, value)

    def clear(self):
        '''
        Clear the list.
        '''
        self._items = []

    def copy(self) -> 'ListProxy':
        '''
        Create a copy of this list.
        '''
        return ListProxy(self.cfg, self.field, self._items)

    def count(self, value: Any) -> int:
        '''
        :returns: count of ``value`` occurrences
        '''
        return self._items.count(value)

    def extend(self, other: Union[list, 'ListProxy']):
        '''
        Extend list by appending elements from the iterable.
        '''
        for item in other:
            self.append(item)

    def index(self, value: Any) -> int:
        '''
        :returns: first index of ``value``
        '''
        return self._items.index(value)

    def insert(self, index, value: Any):
        value = self.field.validate(self.cfg, value)
        self._items.insert(index, value)

    def pop(self, index: int = None):
        return self._items.pop() if index is None else self._items.pop(index)

    def remove(self, value: Any):
        value = self.field.validate(self.cfg, value)
        self._items.remove(value)

    def reverse(self):
        self._items.reverse()

    def sort(self, key=None, reverse=False):
        self._items.sort(key=key, reverse=reverse)


class ListField(Field):
    '''
    A list field that can optionally validate items against a ``Field``. If a field is specified,
    a :class:`ListProxy` will be returned by the ``_validate`` method, which handles individual
    item validation.

    Specifying *required=True* will cause the field validation to validate that the list is not
    ``None`` and is not empty.
    '''

    def __init__(self, field: Field = None, **kwargs):
        '''
        :param field: Field to validate values against
        '''
        super().__init__(**kwargs)
        self.field = field

    def _validate(self, cfg: Config, value: list) -> Union[list, ListProxy]:
        '''
        Validate the value.

        :param cfg: current config
        :param value: value to validate
        :returns: a :class:`list` if not field is specified, a :class:`ListProxy` otherwise
        '''
        if not isinstance(value, (list, tuple)):
            raise ValueError('%s is not a list object' % self.name)

        if self.required and not value:
            raise ValueError('%s is required' % self.name)

        if not self.field or isinstance(self.field, AnyField):
            return value

        value = ListProxy(cfg, self.field, value)
        return value

    def to_basic(self, cfg: Config, value: Union[list, ListProxy]) -> list:
        '''
        Convert to basic type.

        :param cfg: current config
        :param value: value to convert
        '''
        if isinstance(value, ListProxy):
            return value._items
        return value

    def to_python(self, cfg: Config, value: list) -> Union[list, ListProxy]:
        '''
        Convert to Pythonic type.

        :param cfg: current config
        :param value: basic type value
        '''
        if self.field is None or isinstance(self.field, AnyField):
            return value
        return ListProxy(cfg, self.field, value)


class VirtualField(Field):
    '''
    A calculated, readonly field that is not read from or written to a configuration file.
    '''

    def __init__(self, getter: Callable[[Config], Any], **kwargs):
        '''
        :param getter: a callable that is called whenever the value is retrieved, the callable
            will receive a single argument: the current :class:`Config`.
        '''
        super().__init__(**kwargs)
        self.getter = getter

    def __setdefault__(self, cfg: Config):
        pass

    def __getval__(self, cfg: Config):
        return self.getter(cfg)

    def __setval__(self, cfg: Config, value: Any):
        raise TypeError('%s is readonly' % self.key)


class DictField(Field):
    '''
    A generic :class:`dict` field. Individual key/value pairs are not validated. So, this field
    should only be used when a configuration field is completely dynamic.

    Specifying *required=True* will cause the field validation to validate that the ``dict`` is
    not ``None`` and is not empty.
    '''

    def _validate(self, cfg: Config, value: dict) -> dict:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''
        if not isinstance(value, dict):
            raise ValueError('%s is not a dict object' % self.name)

        if self.required and not value:
            raise ValueError('%s is required' % self.name)

        return value


class BoolField(Field):
    '''
    A boolean field.
    '''
    #: Accepted values that evaluate to ``True``
    TRUE_VALUES = ('t', 'true', '1', 'on', 'yes', 'y')
    #: Accepted values that evaluate to ``False``
    FALSE_VALUES = ('f', 'false', '0', 'off', 'no', 'n')

    def _validate(self, cfg: Config, value: str) -> bool:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''

        if isinstance(value, (int, float)):
            value = bool(value)
        elif isinstance(value, str):
            if value.lower() in self.TRUE_VALUES:
                value = True
            elif value.lower() in self.FALSE_VALUES:
                value = False
            else:
                raise ValueError('%s is not a valid boolean' % self.name)
        elif not isinstance(value, bool):
            raise ValueError('%s is not a valid boolean' % self.name)
        return value
