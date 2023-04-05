#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Dict field.
'''
from typing import Optional, Mapping, TypeVar, Any, Tuple, Union, Sequence, Dict, List
from ..core import Field, Config, AnyField, ValidationError

_KeyT = TypeVar('_KeyT')
_ValueT = TypeVar('_ValueT')
KeyValuePairs = Union[Dict[Any, Any], Sequence[Tuple[Any, Any]]]


def _iterate_dict_like(iterable: KeyValuePairs) -> List[Tuple[Any, Any]]:
    if isinstance(iterable, dict):
        return list(iterable.items())
    return list(iterable)



class DictProxy(dict):
    '''
    A Field-validated :class:`list` proxy. This proxy supports all methods that the builtin
    ``list`` supports with the added ability to validate items against a :class:`Field`. This is
    the field returned by the :class:`ListField` validation chain.
    '''

    def __init__(self, cfg: Config, dict_field: 'DictField',
                 iterable: Optional[KeyValuePairs] = None):
        iterable = iterable or []
        self.cfg = cfg
        self.dict_field = dict_field
        if not self.dict_field._use_proxy:
            raise TypeError('DictProxy requires a parent DictField.{key,value}_field attribute')

        if isinstance(iterable, DictProxy) and iterable.dict_field is dict_field:
            super().__init__(iterable)
        elif iterable:
            super().__init__([self._validate(key, value)
                              for key, value in _iterate_dict_like(iterable)])
        else:
            super().__init__()

    @property
    def key_field(self) -> Field:
        '''
        :returns: the field for each item stored in the list.
        '''
        return self.dict_field.key_field  # type: ignore

    @property
    def value_field(self) -> Field:
        '''
        :returns: the field for each item stored in the list.
        '''
        return self.dict_field.value_field  # type: ignore

    def update(self, iterable: KeyValuePairs, **kwargs) -> None:
        if isinstance(iterable, DictProxy) and iterable.dict_field is self.dict_field:
            super().update(iterable)
        else:
            super().update([self._validate(key, value)
                            for key, value in _iterate_dict_like(iterable)])

        for key, value in kwargs.items():
            self.__setitem__(key, value)

    def copy(self) -> 'DictProxy':
        return DictProxy(self.cfg, self.dict_field, self)

    def __setitem__(self, key: Any, value: Any) -> None:
        key, value = self._validate(key, value)
        super().__setitem__(key, value)

    def _ref_path(self, key: str) -> str:
        return "%s[%s]" % (self.dict_field._ref_path, key)

    def _validate(self, key: Any, value: Any) -> Tuple[Any, Any]:
        try:
            validated_key = self.key_field.validate(self.cfg, key)
        except Exception as exc:
            raise ValidationError(self.cfg, self.dict_field, 'invalid dictionary key: %s' % exc,
                                  ref_path=self._ref_path(key))

        try:
            validated_value = self.value_field.validate(self.cfg, value)
        except Exception as exc:
            raise ValidationError(self.cfg, self.dict_field, 'invalid dictionary value: %s' % exc,
                                 ref_path=self._ref_path(key))

        return (validated_key, validated_value)

    def setdefault(self, key: Any, value: Any) -> None:
        key, value = self._validate(key, value)
        super().setdefault(key, value)


class DictField(Field):
    '''
    A generic :class:`dict` field. Individual key/value pairs are not validated. So, this field
    should only be used when a configuration field is completely dynamic.

    Specifying *required=True* will cause the field validation to validate that the ``dict`` is
    not ``None`` and is not empty.
    '''
    storage_type = dict

    def __init__(self, key_field: Optional[Field] = None, value_field: Optional[Field] = None,
                 **kwargs):
        if key_field or value_field:
            self._use_proxy = True
            self.key_field = key_field or AnyField()
            self.value_field = value_field or AnyField()
        else:
            self.key_field = None
            self.value_field = None
            self._use_proxy = False
        super().__init__(**kwargs)

    def _validate(self, cfg: Config, value: dict) -> dict:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''
        if not isinstance(value, dict):
            raise ValueError('value is not a dict object')

        if self.required and not value:
            raise ValueError('value is required')

        if not self._use_proxy:
            return value

        return DictProxy(cfg, self, value)

    def __setdefault__(self, cfg: Config) -> None:
        default = self.default
        if isinstance(default, dict) and self._use_proxy:
            default = DictProxy(cfg, self, default)

        cfg._set_default_value(self._key, default)

    def to_basic(self, cfg: Config, value: Union[dict, DictProxy]) -> dict:
        '''
        Convert to basic type.

        :param cfg: current config
        :param value: value to convert
        '''
        if value is None:
            return value
        if not value:
            return {}

        if not self._use_proxy:
            return dict(value)

        return {self.key_field.to_basic(key): self.value_field.to_basic(value)
                for key, value in value.items()}

    def to_python(self, cfg: Config, value: dict) -> Union[dict, DictProxy]:
        '''
        Convert to Pythonic type.

        :param cfg: current config
        :param value: basic type value
        '''
        if not self._use_proxy:
            return value
        return DictProxy(cfg, self, value)
