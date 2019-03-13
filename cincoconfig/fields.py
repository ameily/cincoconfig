#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

from .abc import Field

__all__ = ('StringField', 'IntField', 'FloatField', 'PortField', 'IPv4AddressField',
           'IPv4NetworkField', 'FilenameField', 'BoolField', 'UrlField', 'AnyField', 'ListField',
           'DynamicField')


class StringField(Field):
    pass


class NumberField(Field):
    pass


class IntField(NumberField):
    pass


class FloatField(NumberField):
    pass


class PortField(IntField):
    pass


class IPv4AddressField(Field):
    pass


class IPv4NetworkField(StringField):
    pass


class FilenameField(StringField):
    pass


class BoolField(Field):
    pass


class UrlField(StringField):
    pass


class ListField(Field):
    pass


class AnyField(Field):
    pass


class DynamicField(Field):
    pass
