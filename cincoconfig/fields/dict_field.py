#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
"""
Dict field.
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple, TypeVar, Union

from ..core import AnyField, Config, Field, ValidationError

_KeyT = TypeVar("_KeyT")
_ValueT = TypeVar("_ValueT")
KeyValuePairs = Union[Dict[Any, Any], Sequence[Tuple[Any, Any]]]


def _iterate_dict_like(iterable: KeyValuePairs) -> List[Tuple[Any, Any]]:
    if isinstance(iterable, dict):
        return list(iterable.items())
    return list(iterable)


class DictProxy(dict):
    """
    A Field-validated :class:`dict` proxy. This proxy supports all methods that the builtin
    ``dict`` supports with the added ability to validate keys and values against a :class:`Field`.
    This is the value returned by the :class:`DictField` validation chain.
    """

    def __init__(
        self,
        cfg: Config,
        dict_field: "DictField",
        iterable: Optional[KeyValuePairs] = None,
    ):
        iterable = iterable or []
        self.cfg = cfg
        self.dict_field = dict_field
        if not self.dict_field._use_proxy:
            raise TypeError(
                "DictProxy requires a parent DictField.{key,value}_field attribute"
            )

        if isinstance(iterable, DictProxy) and iterable.dict_field is dict_field:
            super().__init__(iterable)
        elif iterable:
            super().__init__(
                [
                    self._validate(key, value)
                    for key, value in _iterate_dict_like(iterable)
                ]
            )
        else:
            super().__init__()

    @property
    def key_field(self) -> Field:
        """
        :returns: the field for each item stored in the list.
        """
        return self.dict_field.key_field  # type: ignore

    @property
    def value_field(self) -> Field:
        """
        :returns: the field for each item stored in the list.
        """
        return self.dict_field.value_field  # type: ignore

    def _is_compatible_proxy(self, other: "DictProxy") -> bool:
        """
        Check if a proxy is compatible with this proxy. Two proxies are compatible when they share
        the same configuration object and the same parent :class:`DictField`.
        """
        return self.cfg is other.cfg and self.dict_field is other.dict_field

    def update(self, iterable: Optional[KeyValuePairs] = None, **kwargs) -> None:
        if iterable:
            if isinstance(iterable, DictProxy) and self._is_compatible_proxy(iterable):
                for key, value in iterable.items():
                    super().__setitem__(key, value)
            else:
                super().update(
                    [
                        self._validate(key, value)
                        for key, value in _iterate_dict_like(iterable)
                    ]
                )

        for key, value in kwargs.items():
            self.__setitem__(key, value)

    def copy(self) -> "DictProxy":
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
            raise ValidationError(
                self.cfg,
                self.dict_field,
                "invalid dictionary key: %s" % exc,
                ref_path=self._ref_path(key),
            )

        try:
            validated_value = self.value_field.validate(self.cfg, value)
        except Exception as exc:
            raise ValidationError(
                self.cfg,
                self.dict_field,
                "invalid dictionary value: %s" % exc,
                ref_path=self._ref_path(key),
            )

        return (validated_key, validated_value)

    def setdefault(self, key: Any, value: Any) -> None:
        key, value = self._validate(key, value)
        super().setdefault(key, value)

    def __eq__(self, other: Any) -> bool:
        if other is None or not isinstance(other, dict):
            return False

        if isinstance(other, DictProxy):
            return self._is_compatible_proxy(other) and super().__eq__(other)

        return super().__eq__(other)


class DictField(Field):
    """
    A generic :class:`dict` field that optionally validates keys and values. The ``key_field`` and
    ``value_field`` parameters control whether and how the dictionary keys and values are
    validated, respectively. Setting these will cause the internal representation to be stored in a
    :class:`DictProxy` which handles the validation operations.

    Specifying *required=True* will cause the field validation to validate that the ``dict`` is
    not ``None`` and is not empty.
    """

    storage_type = dict

    def __init__(
        self,
        key_field: Optional[Field] = None,
        value_field: Optional[Field] = None,
        **kwargs
    ):
        if key_field or value_field:
            self._use_proxy = True
            self.key_field = key_field or AnyField()
            self.value_field = value_field or AnyField()
            self.storage_type = Dict[
                self.key_field.storage_type, self.value_field.storage_type
            ]
        else:
            self.key_field = None
            self.value_field = None
            self._use_proxy = False
        super().__init__(**kwargs)

    def _validate(self, cfg: Config, value: dict) -> dict:
        """
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        """
        if not isinstance(value, dict):
            raise ValueError("value is not a dict object")

        if self.required and not value:
            raise ValueError("value is required")

        if not self._use_proxy:
            return value

        return DictProxy(cfg, self, value)

    def __setdefault__(self, cfg: Config) -> None:
        default = self.default
        if isinstance(default, dict) and self._use_proxy:
            default = DictProxy(cfg, self, default)
        elif default is not None:
            default = dict(default)
        cfg._set_default_value(self._key, default)

    def to_basic(self, cfg: Config, value: Union[dict, DictProxy]) -> dict:
        """
        Convert to basic type.

        :param cfg: current config
        :param value: value to convert
        """
        if value is None:
            return value
        if not value:
            return {}

        if not self._use_proxy:
            return dict(value)

        return {
            self.key_field.to_basic(cfg, key): self.value_field.to_basic(cfg, val)  # type: ignore
            for key, val in value.items()
        }

    def to_python(self, cfg: Config, value: dict) -> Union[dict, DictProxy]:
        """
        Convert to Pythonic type.

        :param cfg: current config
        :param value: basic type value
        """
        if not self._use_proxy:
            return value
        return DictProxy(cfg, self, value)
