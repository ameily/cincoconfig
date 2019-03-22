#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Cinco Config Fields.
'''

import os
import re
import socket
import hashlib
import base64
from ipaddress import IPv4Address, IPv4Network
from urllib.parse import urlparse
from typing import Union, List, Any, Iterator, Callable
from .abc import Field, AnyField
from .config import Config, Schema


__all__ = ('StringField', 'IntField', 'FloatField', 'PortField', 'IPv4AddressField',
           'IPv4NetworkField', 'FilenameField', 'BoolField', 'UrlField', 'ListField',
           'HostnameField', 'DictField', 'ListProxy', 'VirtualField', 'ApplicationModeField',
           'LogLevelField', 'SecureStringField')


class StringField(Field):
    '''
    A string field.
    '''

    def __init__(self, *, min_len: int = None, max_len: int = None, regex: str = None,
                 choices: List[str] = None, transform_case: str = None,
                 transform_strip: Union[bool, str] = None, **kwargs):
        '''
        The string field can perform transformations on the value prior to validating it if either
        *transform_case* or *transform_strip* are specified.

        :param min_len: minimum allowed length
        :param max_len: maximum allowed length
        :param regex: regex pattern that the value must match
        :param choices: list of valid choices
        :param transform_case: transform the value's case to either ``upper`` or ``lower`` case
        :param transform_strip: strip the value by calling :meth:`str.strip`.
            Setting this to ``True`` will call :meth:`str.strip` without any arguments (ie.
            striping all whitespace characters) and if this is a ``str``, then :meth:`str.strip`
            will be called with ``transform_strip``.
        '''
        super().__init__(**kwargs)
        self.min_len = min_len
        self.max_len = max_len
        self.regex = re.compile(regex) if regex else None
        self.choices = choices
        self.transform_case = transform_case.lower() if transform_case else None
        self.transform_strip = transform_strip

        if self.transform_case and self.transform_case not in ('lower', 'upper'):
            raise TypeError('transform_case must be "lower" or "upper"')

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        if self.transform_strip:
            if isinstance(self.transform_strip, str):
                value = value.strip(self.transform_strip)
            else:
                value = value.strip()

        if self.transform_case:
            value = value.lower() if self.transform_case == 'lower' else value.upper()

        if self.min_len is not None and len(value) < self.min_len:
            raise ValueError('%s must be at least %d characters' % (self.name, self.min_len))

        if self.max_len is not None and len(value) > self.max_len:
            raise ValueError('%s must not be more than %d chatacters' % (self.name, self.max_len))

        if self.regex and not self.regex.match(value):
            raise ValueError('%s does not match pattern %s' % (self.name, self.regex.pattern))

        if self.choices and value not in self.choices:
            raise ValueError('%s is not a valid choice' % self.name)

        return value


class SecureStringField(Field):
    '''
    A string field that will be encrypted/hashed when written to disk
    '''

    HASH_ACTION = [
        'hash_md5', 'hash_sha1', 'hash_sha224',
        'hash_sha256', 'hash_sha384', 'hash_sha512'
    ]
    ENC_ACTION = ['enc_xor', 'enc_aes256']

    def __init__(self, action: str = None, **kwargs):
        '''
        The *action* parameter is used to specify how the field should be secured. Valid
        values for *action* are:

        * Encryption:
            1. ``enc_xor``
            2. ``enc_aes256`` (requires that *pycrypto* is installed)
        * Hashing:
            1. ``hash_md5``
            2. ``hash_sha1``
            3. ``hash_sha224``
            4. ``hash_sha256``
            5. ``hash_sha384``
            6. ``hash_sha512``

        Using a hashing algorithm will result in data loss since there will be no way
        to get the original value back. Use cases for a hash algorithm on a config field
        could be for a field that is used to validate user provided credentials.

        :param action: specifies how to secure the field (default will be ``hash_sha256``)
        '''
        super().__init__(**kwargs)
        self.action = action or 'hash_sha256'
        self.hashed = False  # Whether or not we've already hashed a value

        if self.action not in self.HASH_ACTION + self.ENC_ACTION:
            raise TypeError('action must be one of the valid hash or encryption algorithms')

        method = 'hash' if self.action in self.HASH_ACTION else 'enc'

        if method == 'enc' and self.action != 'enc_xor':
            # Need to make sure pycrypto is installed
            try:
                from Crypto.Cipher import AES  # pylint: disable=unused-import
            except ImportError:
                raise TypeError('action %s requires the pycrypto module')
        elif method == 'enc':
            # TODO: Generate a key file
            self._generate_key_file()

    def __eq__(self, other: Any) -> bool:
        '''
        Handle equals check in hash mode
        '''
        if isinstance(other, str) and self.action in self.HASH_ACTION:
            other = self._hash(other)
        return getattr(self, self.key) == other

    def _generate_key_file(self, must_exist=False):
        '''
        TODO: Generate or load an application specific key file
        '''
        return b'B' * 32

    def __setdefault__(self, cfg: Config):
        '''
        Set the default value for a secure field

        :param cfg: current config
        '''
        if self.default is None:
            super().__setdefault__(cfg)
            return

        if self.action in self.HASH_ACTION:
            cfg._data[self.key] = self._hash(self.default)
        elif self.action in self.ENC_ACTION:
            cfg._data[self.key] = self._encrypt(self.default)

    def __getval__(self, cfg: Config) -> Any:
        '''
        Retrieve the value and decrypt it if it's not a hashed value

        :param cfg: current config
        :returns: decrypted value if possible
        '''
        if cfg._data[self.key] is None:
            return None

        if self.action in self.ENC_ACTION:
            return self._decrypt(cfg._data[self.key])

        return cfg._data[self.key]

    def _encrypt(self, value: str) -> str:
        '''
        Encrypt the value

        :param value: value to encrypt
        :returns: encrypted value
        '''
        if self.action == "enc_aes256":
            from Crypto.Cipher import AES

            ivec = os.urandom(AES.block_size)

            # TODO: Use key from generated key file
            obj = AES.new(self._generate_key_file(), AES.MODE_CFB, ivec)
            ciphertext = obj.encrypt(value)
            return base64.b64encode(ivec + ciphertext).decode()
        if self.action == "enc_xor":
            return value  # TODO: implement XOR to support no-dependency encryption

        raise TypeError('invalid encryption action %s' % self.action)

    def _decrypt(self, value: str) -> str:
        '''
        Decrypt the value

        :param value: value to decrypt
        :returns: decrypted value
        '''
        if self.action == "enc_aes256":
            from Crypto.Cipher import AES

            ciphertext = base64.b64decode(value.encode())
            ivec = ciphertext[:AES.block_size]
            ciphertext = ciphertext[AES.block_size:]

            # TODO: Use key from generated key file
            obj = AES.new(self._generate_key_file(must_exist=True), AES.MODE_CFB, ivec)
            return obj.decrypt(ciphertext).decode()
        if self.action == "enc_xor":
            return value  # TODO: implement XOR to support no-dependency encryption

        raise TypeError('invalid encryption action %s' % self.action)

    def _hash(self, value: str) -> str:  # pylint: disable=too-many-return-statements
        '''
        Hash the value

        :param value: value to hash
        :returns: hashed value
        '''
        if self.hashed:
            return value

        self.hashed = True

        # TODO: Salt the hashes

        if self.action == "hash_md5":
            return hashlib.md5(value.encode()).hexdigest()
        if self.action == "hash_sha1":
            return hashlib.sha1(value.encode()).hexdigest()
        if self.action == "hash_sha224":
            return hashlib.sha224(value.encode()).hexdigest()
        if self.action == "hash_sha256":
            return hashlib.sha256(value.encode()).hexdigest()
        if self.action == "hash_sha384":
            return hashlib.sha384(value.encode()).hexdigest()
        if self.action == "hash_sha512":
            return hashlib.sha512(value.encode()).hexdigest()

        self.hashed = False
        raise TypeError('invalid hash action %s' % self.action)

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        if value is None:
            self.hashed = False
            return value

        if self.action in self.HASH_ACTION:
            if value != cfg._data[self.key]:
                self.hashed = False
            return self._hash(value)
        if self.action in self.ENC_ACTION:
            return self._encrypt(value)

        raise TypeError("unknown action %s" % self.action)

    def to_basic(self, cfg: Config, value: str) -> dict:
        '''
        Convert to a dict and indicate the type so we know
        on load whether we've already dealt with the field

        :param cfg: current config
        :param value: value to encrypt/hash
        :returns: encrypted/hashed value
        '''
        if value is None:
            return value

        if self.action in self.ENC_ACTION:
            value = self._encrypt(value)
        if self.action in self.HASH_ACTION:
            value = self._hash(value)

        return {
            "type": "secure_value",
            "value": value
        }

    def to_python(self, cfg: Config, value: Union[dict, str]) -> str:
        '''
        Decrypt the value if loading something we've already handled.
        Hash the value if it hasn't been hashed yet.

        :param cfg: current config
        :param value: value to decrypt/load
        :returns: decrypted value or unmodified hash
        '''
        if value is None:
            return value

        if isinstance(value, dict) and value.get("type", "") == "secure_value":
            if self.action in self.HASH_ACTION:
                self.hashed = True
                cfg._data[self.key] = value.get("value")  # So we don't hash again in _validate()
                return value.get("value")  # Can't decrypt a hash
            if self.action in self.ENC_ACTION:
                return self._decrypt(value.get("value"))

            raise TypeError("unknown action %s" % self.action)

        if isinstance(value, str):
            if self.action in self.HASH_ACTION:
                # Definetly coming in from a user-modified config. Make sure we hash it
                self.hashed = False
                cfg._data[self.key] = self._hash(value)  # So we don't hash again in _validate()
                return cfg._data[self.key]
            if self.action in self.ENC_ACTION:
                return value  # Don't encrypt here, it'll get encrypted in _validate()

            raise TypeError("unknown action %s" % self.action)

        raise ValueError("unsupported type %s" % type(value))


class LogLevelField(StringField):
    '''
    A field representing the Python log level.
    '''

    def __init__(self, levels: List[str] = None, **kwargs):
        '''
        :param levels: list of log levels. If not specified, the default Python log levels will be
            used: ``debug``, ``info``, ``warning``, ``error``, and ``critical``.
        '''
        if not levels:
            levels = ['debug', 'info', 'warning', 'error', 'critical']

        self.levels = levels
        kwargs.setdefault('transform_case', 'lower')
        kwargs.setdefault('transform_strip', True)
        kwargs['choices'] = levels
        super().__init__(**kwargs)


class ApplicationModeField(StringField):
    '''
    A field representing the application operating mode.
    '''
    HELPER_MODE_PATTERN = re.compile('^[a-zA-Z0-9_]+$')

    def __init__(self, modes: List[str] = None, create_helpers: bool = True, **kwargs):
        '''
        The *create_helpers* parameter will create a boolean :class:`VirtualField` for each
        ``mode`` named ``is_<mode>_mode``, that returns ``True`` when the mode is active. When
        *create_helpers=True* then each mode name must be a valid Python variable name.

        :param modes: application modes, if not specified the default modes will be used:
            ``production`` and ``development``
        :param create_helpers: create helper a bool ``VirtualField`` for each mode
        '''
        if not modes:
            modes = ['development', 'production']

        self.modes = modes
        self.create_helpers = create_helpers

        if create_helpers:
            for mode in modes:
                if not self.HELPER_MODE_PATTERN.match(mode):
                    raise TypeError('invalid mode name: %s' % mode)

        kwargs.setdefault('transform_case', 'lower')
        kwargs.setdefault('transform_strip', True)
        kwargs['choices'] = modes
        super().__init__(**kwargs)

    def _create_helper(self, mode: str) -> 'VirtualField':
        '''
        Create helper VirtualField.
        '''
        return VirtualField(lambda cfg: cfg[self.key] == mode)

    def __setkey__(self, schema: Schema, key: str):
        '''
        Set the key and optionally add ``VirtualField`` helpers to the schema if
        *create_helpers=True*.
        '''
        self.key = key
        if self.create_helpers:
            for mode in self.modes:
                schema._add_field('is_%s_mode' % mode, self._create_helper(mode))


class NumberField(Field):
    '''
    Base class for all number fields. This field should not be used directly, instead consider
    using :class:`~cincoconfig.IntField` or :class:`~cincoconfig.FloatField`.
    '''

    def __init__(self, type_cls: type, *, min: Union[int, float] = None,
                 max: Union[int, float] = None, **kwargs):
        '''
        :param type_cls: number type class that values will be converted to
        :param min: minimum value
        :param max: maxium value
        '''
        super().__init__(**kwargs)
        self.type_cls = type_cls
        self.min = min
        self.max = max

    def _validate(self, cfg: Config, value: Union[str, int, float]) -> Union[int, float]:
        '''
        Validate the value. This method first converts the value to ``type_class`` and then checks
        the value against ``min`` and ``max`` if they are specified.

        :param cfg: current Config
        :param value: value to validate
        '''
        try:
            value = self.type_cls(value)
        except:
            raise ValueError('%s is not a valid %s' % (self.name, self.type_cls.__name__))

        if self.min is not None and value < self.min:
            raise ValueError('%s must be >= %s' % (self.name, self.min))

        if self.max is not None and value > self.max:
            raise ValueError('%s must be <= %s' % (self.name, self.max))

        return value


class IntField(NumberField):
    '''
    Integer field.
    '''

    def __init__(self, **kwargs):
        super().__init__(int, **kwargs)


class FloatField(NumberField):
    '''
    Float field.
    '''

    def __init__(self, **kwargs):
        super().__init__(float, **kwargs)


class PortField(IntField):
    '''
    Network port field.
    '''

    def __init__(self, **kwargs):
        kwargs.setdefault('min', 1)
        kwargs.setdefault('max', 65535)
        super().__init__(**kwargs)


class IPv4AddressField(StringField):
    '''
    IPv4 address field.
    '''

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        try:
            addr = IPv4Address(value)
        except:
            raise ValueError('%s must be a valid IPv4 address' % self.name)
        return str(addr)


class IPv4NetworkField(StringField):
    '''
    IPv4 network field. This field accepts CIDR notation networks in the form of ``A.B.C.D/Z``.
    '''

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        try:
            net = IPv4Network(value)
        except:
            raise ValueError('%s must be a valid IPv4 Network (CIDR notation)' % self.name)
        return str(net)


class HostnameField(StringField):
    '''
    A field representing a network hostname or, optionally, a network address.
    '''
    HOSTNAME_REGEX = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9.\-]+$')
    NETBIOS_REGEX = re.compile(r"^[\w!@#$%^()\-'{}\.~]{1,15}$")

    def __init__(self, *, allow_ipv4: bool = True, resolve: bool = False, **kwargs):
        '''
        :param allow_ipv4: allow both a hostname and an IPv4 address
        :param resolve: resolve hostnames to their IPv4 address and raise a :class:`ValueError`
            if the resolution fails
        '''
        super().__init__(**kwargs)
        self.allow_ipv4 = allow_ipv4
        self.resolve = resolve

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to valdiate
        '''
        try:
            addr = IPv4Address(value)
        except:
            pass
        else:
            if self.allow_ipv4:
                return str(addr)
            raise ValueError('%s is not a valid DNS hostname')

        # value is a hostname
        if self.resolve:
            # resolve hostname to IPv4 address
            try:
                name = socket.gethostbyname(value)
            except:
                raise ValueError('%s DNS resolution failed' % self.name)
            else:
                return name

        # Validate that the value *looks* like a DNS hostname or Windows NetBios name
        dns_match = self.HOSTNAME_REGEX.match(value)
        nb_match = self.NETBIOS_REGEX.match(value)
        if not dns_match and not nb_match:
            raise ValueError('%s is not a valid hostname')

        return value


class FilenameField(StringField):
    '''
    A field for representing a filename on disk.
    '''

    def __init__(self, *, exists: Union[bool, str] = None, startdir: str = None, **kwargs):
        '''
        The *exists* parameter can be set to one of the following values:

        - ``None`` - don't check file's existance
        - ``False`` - validate that the filename does not exist
        - ``True`` - validate that the filename does exist
        - ``dir`` - validate that the filename is a directory that exists
        - ``file`` - validate that the filename is a file that exists

        The *startdir* parameter, if specified, will resolve filenames starting from a directory
        and will cause all filenames to be validated to their absolute file path. If not specified,
        filename's will be resolved relative to :meth:`os.getcwd` and the relative file path will
        be validated.

        :param exists: validate the filename's existence on disk
        :param startdir: resolve relative paths to a start directory
        '''
        super().__init__(**kwargs)
        self.exists = exists
        self.startdir = startdir

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''
        if not os.path.isabs(value) and self.startdir:
            value = os.path.abspath(os.path.join(self.startdir, value))

        if os.path.sep == '\\':
            value = value.replace('/', '\\')

        value_exists = os.path.exists(value)
        if self.exists is True and not value_exists:
            raise ValueError('%s file or directory does not exist' % self.name)
        if self.exists is False and value_exists:
            raise ValueError('%s file or directory already exists' % self.name)
        if self.exists == 'dir' and not os.path.isdir(value):
            raise ValueError('%s directory %s' %
                             (self.name, 'already exists' if value_exists else 'does not exist'))
        if self.exists == 'file' and not os.path.isfile(value):
            raise ValueError('%s file %s' %
                             (self.name, 'already exists' if value_exists else 'does not exist'))

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


class UrlField(StringField):
    '''
    A URL field. Values are validated that they are both a valid URL and contain a valid scheme.
    '''

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate the value.

        :param cfg: current config
        :param value: value to validate
        '''
        try:
            url = urlparse(value)
            if not url.scheme:
                raise ValueError('no scheme url scheme')
        except:
            raise ValueError('%s is not a valid URL' % self.name)
        return value


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
