#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
List field
'''
import inspect
from typing import Iterable, TypeVar, Type, Union, Any, List
from ..core import (ContainerValueMixin, Field, Config, BaseField, Schema, isconfigtype, AnyField,
                    ConfigType)


_T = TypeVar('_T')


class ListProxy(list, ContainerValueMixin):
    '''
    A Field-validated :class:`list` proxy. This proxy supports all methods that the builtin
    ``list`` supports with the added ability to validate items against a :class:`Field`. This is
    the field returned by the :class:`ListField` validation chain.
    '''

    def __init__(self, cfg: Config, list_field: 'ListField', iterable: Iterable[_T] = None):
        iterable = iterable or []
        self.cfg = cfg
        self.list_field = list_field
        if not self.list_field.field:
            raise TypeError('ListProxy requires a parent ListField.field attribute')

        if isinstance(iterable, ListProxy) and iterable.item_field is list_field.field:
            super().__init__(iterable)
        else:
            super().__init__(self._validate(item)
                             for index, item in enumerate(iterable))

    @property
    def item_field(self) -> Union[BaseField, Type[Config]]:
        '''
        :returns: the field for each item stored in the list.
        '''
        return self.list_field.field  # type: ignore

    def append(self, item: _T) -> None:
        super().append(self._validate(item))

    def extend(self, iterable: Iterable[_T]) -> None:
        if isinstance(iterable, ListProxy) and iterable.item_field is self.item_field:
            super().extend(iterable)
        else:
            super().extend(self._validate(item) for item in iterable)

    def insert(self, index: int, item: _T) -> None:
        super().insert(index, self._validate(item))

    def copy(self) -> 'ListProxy':
        return ListProxy(self.cfg, self.list_field, self)

    def __iadd__(self, iterable: Iterable[_T]) -> 'ListProxy':
        self.extend(iterable)
        return self

    def __add__(self, iterable: Iterable[_T]) -> 'ListProxy':
        ret = self.copy()
        ret.extend(iterable)
        return ret

    def __setitem__(self, index: Union[int, slice],  # type: ignore[override]
                    item: Union[_T, Iterable[_T]]) -> None:
        if isinstance(index, slice) and isinstance(item, (list, tuple)):
            super().__setitem__(index, [self._validate(i) for i in item])
        elif isinstance(index, int):
            super().__setitem__(index, self._validate(item))

    def _validate(self, value: Any) -> Any:
        '''
        Validate a value.

        :param value: value to validate
        :returns: the validated value
        '''
        if isinstance(self.item_field, Schema) or isconfigtype(self.item_field):
            if isinstance(value, dict):
                cfg = self.item_field()  # type: ignore
                cfg._container = self
                cfg._key = self.list_field._key
                cfg._parent = self.cfg
                cfg.load_tree(value)  # type: ignore
            elif isinstance(value, Config):
                value._parent = self.cfg
                value._key = self.list_field._key
                value._container = self
                value.validate()
                cfg = value
            else:
                raise ValueError('invalid configuration object')

            return cfg

        if isinstance(self.item_field, Field):
            return self.item_field.validate(self.cfg, value)

        # we should only hit this when item_field is not a field, schema, or ConfigType subclass
        # (which shouldn't happen)
        raise TypeError('item field must be a Field, Schema, or ConfigType subclass: %s' %
                        self.item_field)

    def _get_item_position(self, item: Any) -> str:
        try:
            return str(self.index(item))
        except:
            return str(len(self))


class ListField(Field):
    '''
    A list field that can optionally validate items against a ``Field``. If a field is specified,
    a :class:`ListProxy` will be returned by the ``_validate`` method, which handles individual
    item validation.

    Specifying *required=True* will cause the field validation to validate that the list is not
    ``None`` and is not empty.
    '''
    storage_type = List

    def __init__(self, field: Union[BaseField, Type[ConfigType]] = None, **kwargs):
        '''
        :param field: Field to validate values against
        '''
        super().__init__(**kwargs)
        self.field = field

        if field:
            if isinstance(field, Field):
                self.storage_type = List[field.storage_type]  # type: ignore
            elif inspect.isclass(field):
                self.storage_type = List[field]  # type: ignore
            else:
                self.storage_type = List[type(field)]  # type: ignore

    def __setdefault__(self, cfg: Config) -> None:
        default = self.default
        if isinstance(default, list) and self.field:
            default = ListProxy(cfg, self, default)

        cfg._data[self._key] = default

    def _validate(self, cfg: Config, value: list) -> Union[list, ListProxy]:
        '''
        Validate the value.

        :param cfg: current config
        :param value: value to validate
        :returns: a :class:`list` if not field is specified, a :class:`ListProxy` otherwise
        '''
        if not isinstance(value, (list, tuple)):
            raise ValueError('value is not a list')

        if self.required and not value:
            raise ValueError('value is required')

        if not self.field or isinstance(self.field, AnyField):
            return value

        proxy = ListProxy(cfg, self, value)
        return proxy

    def to_basic(self, cfg: Config, value: Union[list, ListProxy]) -> list:
        '''
        Convert to basic type.

        :param cfg: current config
        :param value: value to convert
        '''
        if value is None:
            return value
        if not value:
            return []

        if isinstance(self.field, Schema) or isconfigtype(self.field):
            return [item.to_tree() for item in value]
        if isinstance(self.field, Field):
            return [self.field.to_basic(cfg, item) for item in value]
        return list(value)

    def to_python(self, cfg: Config, value: list) -> Union[list, ListProxy]:
        '''
        Convert to Pythonic type.

        :param cfg: current config
        :param value: basic type value
        '''
        if self.field is None or isinstance(self.field, AnyField):
            return value
        return ListProxy(cfg, self, value)
