#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Instance method
'''
from typing import Any, Callable
from functools import wraps
from ..core import Field, Config, InstanceMethodFieldMixin, Schema


class InstanceMethodField(Field, InstanceMethodFieldMixin):
    '''
    A configuration instance method.
    '''
    storage_type = Callable

    def __init__(self, method: Callable[[Config], Any], **kwargs):
        if kwargs.get('default') is not None:
            raise TypeError('instance methods cannot have a default value')

        super().__init__(**kwargs)
        self.method = method

    def __setdefault__(self, cfg: Config) -> None:
        '''
        Bind the instance method to the configuration. This is a performance enhancement since the
        bound method, created in :meth:`_bind`, is config specific and this method will cache the
        result in the configuration.

        :param cfg: configuration
        '''
        object.__setattr__(cfg, self._key, self._bind(cfg))

    def _bind(self, cfg: Config) -> Callable:
        '''
        Create a bound instance method on the configuration.

        :param cfg: configuration
        :returns: the bound method
        '''
        @wraps(self.method)
        def wrapper(*args, **kwargs) -> Any:
            return self.method(cfg, *args, **kwargs)  # type: ignore

        # wrapper.__name__ = getattr(self.method, '__name__', 'wrapper')
        # wrapper.__doc__ = getattr(self.method, '__doc__', '')
        # wrapper.__annotations__ = getattr(self.method, '__annotations__', {})
        return wrapper

    def validate(self, cfg: Config, value: Any) -> Any:
        return value

    def __setval__(self, cfg: Config, value: Any) -> None:
        raise TypeError('field is readonly')


def instance_method(schema: Schema, name: str) -> Callable:
    def wrapper(func: Callable[[Config], Any]) -> Callable[[Config], Any]:
        schema._add_field(name, InstanceMethodField(method=func))
        return func
    return wrapper
