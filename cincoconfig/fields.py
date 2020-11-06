#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Cinco Config Fields.
'''
# This is temporary. Will be fixed with issue #9
# pylint: disable=too-many-lines

import os
import re
import socket
import base64
import binascii
from ipaddress import IPv4Address, IPv4Network
from urllib.parse import urlparse
from typing import Union, List, Any, Callable, NamedTuple, Optional, Dict, Iterable, TypeVar
import hashlib

from .abc import Field, AnyField, BaseConfig, BaseSchema, ConfigFormat, SchemaField
from .encryption import EncryptionError, SecureValue


__all__ = ('StringField', 'IntField', 'FloatField', 'PortField', 'IPv4AddressField',
           'IPv4NetworkField', 'FilenameField', 'BoolField', 'UrlField', 'ListField',
           'HostnameField', 'DictField', 'ListProxy', 'VirtualField', 'ApplicationModeField',
           'LogLevelField', 'NumberField', 'ChallengeField', 'DigestValue', 'SecureField',
           'BytesField', 'IncludeField', 'InstanceMethodField')

_T = TypeVar('_T')


class StringField(Field):
    '''
    A string field.
    '''
    storage_type = str

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

    def _validate(self, cfg: BaseConfig, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        if not isinstance(value, str):
            raise ValueError('value must be a string, not a %s' % type(value).__name__)

        if self.transform_strip:
            if isinstance(self.transform_strip, str):
                value = value.strip(self.transform_strip)
            else:
                value = value.strip()

        if self.required and not value:
            raise ValueError('value is required')

        if self.transform_case:
            value = value.lower() if self.transform_case == 'lower' else value.upper()

        if self.min_len is not None and len(value) < self.min_len:
            raise ValueError('value must be at least %d characters' % self.min_len)

        if self.max_len is not None and len(value) > self.max_len:
            raise ValueError('value must not be more than %d chatacters' % self.max_len)

        if self.regex and not self.regex.match(value):
            raise ValueError('value does not match pattern %s' % self.regex.pattern)

        if self.choices and value not in self.choices:
            if len(self.choices) < 6:
                postfix = ': must be one of: ' + ', '.join(self.choices)
            else:
                postfix = ''
            raise ValueError('value is not a valid choice' + postfix)

        return value


class LogLevelField(StringField):
    '''
    A field representing the Python log level.
    '''
    storage_type = str

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
    storage_type = str
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
        return VirtualField(lambda cfg: self.__getval__(cfg) == mode)

    def __setkey__(self, schema: BaseSchema, key: str) -> None:
        '''
        Set the key and optionally add ``VirtualField`` helpers to the schema if
        *create_helpers=True*.
        '''
        super().__setkey__(schema, key)
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
        self.storage_type = type_cls

    def _validate(self, cfg: BaseConfig, value: Union[str, int, float]) -> Union[int, float]:
        '''
        Validate the value. This method first converts the value to ``type_class`` and then checks
        the value against ``min`` and ``max`` if they are specified.

        :param cfg: current Config
        :param value: value to validate
        '''
        if not isinstance(value, (str, int, float, self.type_cls)) or isinstance(value, bool):
            raise ValueError('value type %s cannot be converted to %s' %
                             (type(value).__name__, self.type_cls.__name__))

        try:
            num = self.type_cls(value)  # type: Union[int, float]
        except (ValueError, TypeError) as err:
            raise ValueError('value is not a valid %s' % self.type_cls.__name__) from err

        if self.min is not None and num < self.min:
            raise ValueError('value must be >= %s' % self.min)

        if self.max is not None and num > self.max:
            raise ValueError('value must be <= %s' % self.max)

        return num


class IntField(NumberField):
    '''
    Integer field.
    '''
    storage_type = int

    def __init__(self, **kwargs):
        super().__init__(int, **kwargs)


class FloatField(NumberField):
    '''
    Float field.
    '''
    storage_type = float

    def __init__(self, **kwargs):
        super().__init__(float, **kwargs)


class PortField(IntField):
    '''
    Network port field.
    '''
    storage_type = int

    def __init__(self, **kwargs):
        kwargs.setdefault('min', 1)
        kwargs.setdefault('max', 65535)
        super().__init__(**kwargs)


class IPv4AddressField(StringField):
    '''
    IPv4 address field.
    '''
    storage_type = str

    def _validate(self, cfg: BaseConfig, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        value = super()._validate(cfg, value)

        try:
            addr = IPv4Address(value)
        except ValueError as err:
            raise ValueError('value is not a valid IPv4 address') from err
        return str(addr)


class IPv4NetworkField(StringField):
    '''
    IPv4 network field. This field accepts CIDR notation networks in the form of ``A.B.C.D/Z``.
    '''
    storage_type = str

    def _validate(self, cfg: BaseConfig, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        value = super()._validate(cfg, value)

        try:
            net = IPv4Network(value)
        except ValueError as err:
            raise ValueError('value is not a valid IPv4 Network (CIDR)') from err
        return str(net)


class HostnameField(StringField):
    '''
    A field representing a network hostname or, optionally, a network address.
    '''
    storage_type = str
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

    def _validate(self, cfg: BaseConfig, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to valdiate
        '''
        value = super()._validate(cfg, value)

        try:
            addr = IPv4Address(value)
        except:
            pass
        else:
            if self.allow_ipv4:
                return str(addr)
            raise ValueError('value is not a valid DNS hostname')

        # value is a hostname
        if self.resolve:
            # resolve hostname to IPv4 address
            try:
                name = socket.gethostbyname(value)
            except OSError as err:
                raise ValueError('DNS resolution failed') from err
            else:
                return name

        # Validate that the value *looks* like a DNS hostname or Windows NetBios name
        dns_match = self.HOSTNAME_REGEX.match(value)
        nb_match = self.NETBIOS_REGEX.match(value)
        if not dns_match and not nb_match:
            raise ValueError('value is not a valid hostname')

        return value


class FilenameField(StringField):
    '''
    A field for representing a filename on disk.
    '''
    storage_type = str

    def __init__(self, *, exists: Union[bool, str] = None, startdir: str = None, **kwargs):
        '''
        The *exists* parameter can be set to one of the following values:

        - ``None`` - don't check file's existance
        - ``False`` - validate that the filename does not exist
        - ``True`` - validate that the filename does exist
        - ``"dir"`` - validate that the filename is a directory that exists
        - ``"file"`` - validate that the filename is a file that exists

        The *startdir* parameter, if specified, will resolve filenames starting from a directory
        and will cause all filenames to be validate to their abslute file path. If not specified,
        filename's will be resolve relative to :meth:`os.getcwd` and the relative file path will
        be validated.

        :param exists: validate the filename's existance on disk
        :param startdir: resolve relative paths to a start directory
        '''
        super().__init__(**kwargs)
        self.exists = exists
        self.startdir = startdir

    def _validate(self, cfg: BaseConfig, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''
        value = super()._validate(cfg, value)

        if not value:
            return value

        if not os.path.isabs(value) and self.startdir:
            value = os.path.abspath(os.path.join(self.startdir, value))

        if os.path.sep == '\\':
            value = value.replace('/', '\\')

        value_exists = os.path.exists(value)
        if self.exists is True and not value_exists:
            raise ValueError('file or directory does not exist: %s' % value)
        if self.exists is False and value_exists:
            raise ValueError('file or directory already exists: %s' % value)
        if self.exists == 'dir' and not os.path.isdir(value):
            raise ValueError('directory %s: %s' %
                             ('already exists' if value_exists else 'does not exist', value))
        if self.exists == 'file' and not os.path.isfile(value):
            raise ValueError('file %s: %s' %
                             ('already exists' if value_exists else 'does not exist', value))

        return value


class BoolField(Field):
    '''
    A boolean field.
    '''
    storage_type = bool
    #: Accepted values that evaluate to ``True``
    TRUE_VALUES = ('t', 'true', '1', 'on', 'yes', 'y')
    #: Accepted values that evaluate to ``False``
    FALSE_VALUES = ('f', 'false', '0', 'off', 'no', 'n')

    def _validate(self, cfg: BaseConfig, value: str) -> bool:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''

        if isinstance(value, bool):
            bval = value
        elif isinstance(value, (int, float)):
            bval = bool(value)
        elif isinstance(value, str):
            if value.lower() in self.TRUE_VALUES:
                bval = True
            elif value.lower() in self.FALSE_VALUES:
                bval = False
            else:
                raise ValueError('value is not a valid boolean')
        else:
            raise ValueError('value is not a valid boolean')
        return bval


class UrlField(StringField):
    '''
    A URL field. Values are validated that they are both a valid URL and contain a valid scheme.
    '''
    storage_type = str

    def _validate(self, cfg: BaseConfig, value: str) -> str:
        '''
        Validate the value.

        :param cfg: current config
        :param value: value to validate
        '''
        value = super()._validate(cfg, value)

        try:
            url = urlparse(value)
            if not url.scheme:
                raise ValueError('no scheme url scheme')
        except Exception as err:
            raise ValueError('value is not a valid URL') from err
        return value


class ListProxy(list):
    '''
    A Field-validated :class:`list` proxy. This proxy supports all methods that the builtin
    ``list`` supports with the added ability to validate items against a :class:`Field`. This is
    the field returned by the :class:`ListField` validation chain.
    '''

    def __init__(self, cfg: BaseConfig, field: SchemaField, iterable: Iterable[_T] = None):
        iterable = iterable or []
        self.cfg = cfg
        self.field = field
        if isinstance(iterable, ListProxy) and iterable.field is field:
            super().__init__(iterable)
        else:
            super().__init__(self._validate(item) for item in iterable)

    def append(self, item: _T) -> None:
        super().append(self._validate(item))

    def extend(self, iterable: Iterable[_T]) -> None:
        if isinstance(iterable, ListProxy) and iterable.field is self.field:
            super().extend(iterable)
        else:
            super().extend(self._validate(item) for item in iterable)

    def insert(self, index: int, item: _T) -> None:
        super().insert(index, self._validate(item))

    def copy(self) -> 'ListProxy':
        return ListProxy(self.cfg, self.field, self)

    def __iadd__(self, iterable: Iterable[_T]) -> 'ListProxy':
        self.extend(iterable)
        return self

    def __add__(self, iterable: Iterable[_T]) -> 'ListProxy':
        ret = self.copy()
        ret.extend(iterable)
        return ret

    def __setitem__(self, index: Union[int, slice], item: Union[_T, Iterable[_T]]) -> None:
        if isinstance(index, slice) and isinstance(item, (list, tuple)):
            super().__setitem__(index, [self._validate(i) for i in item])
        else:
            super().__setitem__(index, self._validate(item))

    def _validate(self, value: Any) -> Any:
        '''
        Validate a value.

        :param value: value to validate
        :returns: the validated value
        '''
        if isinstance(self.field, BaseSchema):
            if isinstance(value, dict):
                cfg = self.field()  # type: ignore
                cfg._parent = self.cfg
                cfg.load_tree(value)
            elif isinstance(value, BaseConfig):
                value._parent = self.cfg
                value.validate()
                cfg = value
            else:
                raise ValueError('invalid configuration object')

            return cfg

        return self.field.validate(self.cfg, value)


class ListField(Field):
    '''
    A list field that can optionally validate items against a ``Field``. If a field is specified,
    a :class:`ListProxy` will be returned by the ``_validate`` method, which handles individual
    item validation.

    Specifying *required=True* will cause the field validation to validate that the list is not
    ``None`` and is not empty.
    '''
    storage_type = List

    def __init__(self, field: SchemaField = None, **kwargs):
        '''
        :param field: Field to validate values against
        '''
        super().__init__(**kwargs)
        self.field = field

        if field:
            if isinstance(field, Field):
                self.storage_type = List[field.storage_type]  # type: ignore
            elif isinstance(field, BaseSchema):
                self.storage_type = List[type(field)]  # type: ignore

    def __setdefault__(self, cfg: BaseConfig) -> None:
        default = self.default
        if isinstance(default, list) and self.field:
            default = ListProxy(cfg, self.field, default)

        cfg._data[self.key] = default

    def _validate(self, cfg: BaseConfig, value: list) -> Union[list, ListProxy]:
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

        proxy = ListProxy(cfg, self.field, value)
        return proxy

    def to_basic(self, cfg: BaseConfig, value: Union[list, ListProxy]) -> list:
        '''
        Convert to basic type.

        :param cfg: current config
        :param value: value to convert
        '''
        if value is None:
            return value
        if not value:
            return []

        if isinstance(self.field, BaseSchema):
            return [item.to_tree() for item in value]
        if self.field:
            return [self.field.to_basic(cfg, item) for item in value]
        return list(value)

    def to_python(self, cfg: BaseConfig, value: list) -> Union[list, ListProxy]:
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

    def __init__(self, getter: Callable[[BaseConfig], Any],
                 setter: Callable[[BaseConfig, Any], Any] = None, **kwargs):
        '''
        :param getter: a callable that is called whenever the value is retrieved, the callable
            will receive a single argument: the current :class:`Config`.
        :param setter: a callable that is called whenever the value is set, the callable will
            receive two arguments: ``config, value``, the current :class:`Config` and the value
            being set
        '''
        if kwargs.get('default') is not None:
            raise TypeError('virutal fields cannot have a default value')

        super().__init__(**kwargs)
        self.getter = getter
        self.setter = setter

    def __setdefault__(self, cfg: BaseConfig) -> None:
        pass

    def __getval__(self, cfg: BaseConfig) -> Any:
        return self.getter(cfg)

    def __setval__(self, cfg: BaseConfig, value: Any) -> None:
        if not self.setter:
            raise TypeError('field is readonly')
        self.setter(cfg, value)


class InstanceMethodField(Field):
    '''
    A configuration instance method.
    '''

    def __init__(self, method: Callable[[BaseConfig], Any], **kwargs):
        if kwargs.get('default') is not None:
            raise TypeError('instance methods cannot have a default value')

        super().__init__(**kwargs)
        self.method = method

    def __setdefault__(self, cfg: BaseConfig) -> None:
        '''
        Bind the instance method to the configuration. This is a performance enhancement since the
        bound method, created in :meth:`_bind`, is config specific and this method will cache the
        result in the configuration.

        :param cfg: configuration
        '''
        object.__setattr__(cfg, self.key, self._bind(cfg))

    def _bind(self, cfg: BaseConfig) -> Callable:
        '''
        Create a bound instance method on the configuration.

        :param cfg: configuration
        :returns: the bound method
        '''
        def wrapper(*args, **kwargs) -> Any:
            return self.method(cfg, *args, **kwargs)  # type: ignore

        wrapper.__name__ = getattr(self.method, '__name__', 'wrapper')
        wrapper.__doc__ = getattr(self.method, '__doc__', '')
        wrapper.__annotations__ = getattr(self.method, '__annotations__', {})
        return wrapper

    def __getval__(self, cfg: BaseConfig) -> Callable:
        '''
        Get the bound method. This method should never be called since __setdefault__ caches the
        result in the configuration.
        '''
        return self._bind(cfg)

    def __setval__(self, cfg: BaseConfig, value: Any) -> None:
        raise TypeError('field is readonly')


class DictField(Field):
    '''
    A generic :class:`dict` field. Individual key/value pairs are not validated. So, this field
    should only be used when a configuration field is completely dynamic.

    Specifying *required=True* will cause the field validation to validate that the ``dict`` is
    not ``None`` and is not empty.
    '''
    storage_type = dict

    def _validate(self, cfg: BaseConfig, value: dict) -> dict:
        '''
        Validate a value.

        :param cfg: current config
        :param value: value to validate
        '''
        if not isinstance(value, dict):
            raise ValueError('value is not a dict object')

        if self.required and not value:
            raise ValueError('value is required')

        return value


#: Hash algorithm, as returned by hashlib.new()
HashAlgorithm = Callable[[Optional[bytes]], 'hashlib._Hash']

#: Named tuple for digest, value, algorithm
TDigestValue = NamedTuple('TDigestValue', [
    ('salt', bytes),
    ('digest', bytes),
    ('algorithm', HashAlgorithm)
])


class DigestValue(TDigestValue):
    '''
    Digest value tuple storing hashed value: (salt, digest, algorithm). The digest is the hash
    of the concatenated salt and plaintext value (``hash(salt + plaintext)``).
    '''

    def __str__(self) -> str:
        '''
        :returns: the salt and digest pair, both base64 encoded, separated by a ``:``.
        '''
        return (base64.b64encode(self.salt) + b':' + base64.b64encode(self.digest)).decode()

    @classmethod
    def parse(cls, value: str, algorithm: HashAlgorithm) -> 'DigestValue':
        '''
        Parse a base64-encoded salt/digest pair, as returned by :meth:`__str__`
        '''
        try:
            salt_b64, digest_b64 = value.split(':', 1)
            salt = base64.b64decode(salt_b64)
            digest = base64.b64decode(digest_b64)
        except (ValueError, binascii.Error) as err:
            raise ValueError('invalid salt/digest tuple value') from err

        return DigestValue(salt, digest, algorithm)

    @classmethod
    def create(cls, plaintext: Union[str, bytes], algorithm: HashAlgorithm,
               salt: bytes = None) -> 'DigestValue':
        '''
        Hash a plaintext value and return the new digest value. The digest is calculated as:

        .. code-block:: python

            salt[:digest_size] + plaintext

        The *salt* will be randomly generated if not specified. If the salt is specified and it is
        larger than the algorithm ``digest_size``, the salt will be truncated to the
        ``digest_size``.

        :param plaintext: string to hash
        :param algorithm: hashlib algorithm to use
        :param salt: hash salt
        :returns: the created digest value
        '''

        hasher = algorithm()  # type: ignore
        if salt and len(salt) < hasher.digest_size:
            raise TypeError('salt must be at least %d bytes' % hasher.digest_size)

        if salt:
            salt = salt[:hasher.digest_size]
        else:
            salt = os.urandom(hasher.digest_size)

        if isinstance(plaintext, str):
            plaintext = plaintext.encode()

        hasher.update(salt + plaintext)
        return DigestValue(salt, hasher.digest(), algorithm)

    def challenge(self, plaintext: Union[str, bytes]) -> None:
        '''
        Challenge a plaintext value against the digest value. This will raise a :class:`ValueError`
        if the challenge is unsuccessful.

        :raises ValueError: the challenge was unsuccessful
        '''
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()

        challenge = self.algorithm(self.salt + plaintext).digest()
        if self.digest != challenge:
            raise ValueError('challenge failed')


class ChallengeField(Field):
    '''
    A field whose value is securely stored as a hash (:class:`DigestValue`). This field can be
    used as a secure method of password storage and comparison, since the password is only stored
    in hashed form and not in plaintext. A digest value is pair of salt and
    ``hash(salt + plaintext)`` values.

    Values are stored in memory as :class:`DigestValue` instances. For example:

    .. code-block:: python

        >>> schema = Schema()
        >>> schema.password = ChallengeField('md5')
        >>> cfg = schema()
        >>> cfg.password = "Hello"
        >>> print(type(cfg.password))
        <class 'cincoconfig.fields.DigestValue'>

        >>> print(cfg.password)
        Yt4Qm5cC9FoRSdU3Ly7B7A==:+GXXhO36XvJ446fqXYJ+1w==

        >>> cfg.password.digest
        b'\xf8e\xd7\x84\xed\xfa^\xf2x\xe3\xa7\xea]\x82~\xd7'

    The ``default`` value of a challenge field can be either:

    - A plaintext string. In this case, the salt will be randomly generated.
    - A :class:`DigestValue` instance.

    When the default value is a string, the salt will change between application executions. For
    example:

    .. code-block:: python

        >>> schema = Schema()
        >>> schema.password = ChallengeField('md5', default='hello')
        >>> cfg = schema()
        # First time application executes
        >>> print(cfg.password)
        Yt4Qm5cC9FoRSdU3Ly7B7A==:+GXXhO36XvJ446fqXYJ+1w==

        # Secon time application executes
        >>> print(cfg.password)
        j1DumfRtnRCJxjCAAXzxww==:vKphx3hWXTaOUacYj+4agw==

    Digest values are saved to disk as a :class:`dict` containing two keys:

    - ``salt`` - base64 encoded salt
    - ``digest`` - base64 encoded digest

    The challenge field supports loading plaintext string values from the configuration file. So,
    when manually writting the config file, the user does not need to create the salt and digest
    pair but, instead, just specify a plaintext string to hash. The value will be properly saved
    as a salt/digest pair the next time the config file is saved to disk.

    Available hash algorithms are:

    - md5
    - sha1
    - sha224
    - sha256
    - sha384
    - sha512
    '''
    storage_type = DigestValue

    #: Available hashing algorithms
    ALGORITHMS = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha224': hashlib.sha224,
        'sha256': hashlib.sha256,
        'sha384': hashlib.sha384,
        'sha512': hashlib.sha512
    }  # type: Dict[str, Callable]

    def __init__(self, hash_algorithm: str = 'sha256', **kwargs):
        '''
        :param hash_algorithm: hash algorithm to use, must be a key of :attr:`ALGORITHMS`
        '''
        super().__init__(**kwargs)
        algorithm = self.ALGORITHMS.get(hash_algorithm.lower())
        if not algorithm:
            raise TypeError('Unknown hash algorithm: ' + hash_algorithm)
        self.algorithm = algorithm

    def __setdefault__(self, cfg: BaseConfig) -> None:
        '''
        Set default value by creating a :class:`DigestValue` if the default value is a string.
        '''
        if self.default is None:
            super().__setdefault__(cfg)
            return

        if isinstance(self.default, str):
            val = DigestValue.create(self.default, self.algorithm)
        elif isinstance(self.default, DigestValue):
            val = self.default
        else:
            raise TypeError('invalid default value: %r' % self.default)
        cfg._data[self.key] = val

    def _validate(self, cfg: BaseConfig, value: Any) -> DigestValue:
        '''
        Validate the value. If the value is a plaintext string, a :class:`DigestValue`
        '''
        if isinstance(value, (str, bytes)):
            val = self._hash(value)
        elif isinstance(value, DigestValue):
            val = value
        else:
            raise ValueError('value must be a string, not a %s' % type(value).__name__)
        return val

    def _hash(self, plaintext: Union[str, bytes], salt: bytes = None) -> DigestValue:
        '''
        Private method that performs the actual hash. This method does not
        check if the value has already been hashed.

        :param value: the value to be hashed
        :param salt: specify the salt to use. Used by :meth:`check_hash`
        :raise TypeError: if the action is invalid
        '''

        return DigestValue.create(plaintext, self.algorithm, salt=salt)

    def to_basic(self, cfg: BaseConfig, value: DigestValue) -> dict:
        '''
        Convert to a dict and indicate the type so we know
        on load whether we've already dealt with the field

        :param cfg: current config
        :param value: value to encrypt/hash
        :returns: encrypted/hashed value
        '''
        if value is None:
            return value

        return {
            'salt': base64.b64encode(value.salt).decode(),
            'digest': base64.b64encode(value.digest).decode(),
        }

    def to_python(self, cfg: BaseConfig, value: Union[dict, str]) -> DigestValue:
        '''
        Decrypt the value if loading something we've already handled.
        Hash the value if it hasn't been hashed yet.

        :param cfg: current config
        :param value: value to decrypt/load
        :returns: decrypted value or unmodified hash
        :raises ValueError: if the value read from the config is neither a dict nor a string
        '''
        if value is None:
            return value

        if isinstance(value, dict):
            try:
                salt = base64.b64decode(value['salt'])
            except (KeyError, binascii.Error) as err:
                raise ValueError('%s: invalid salt: salt must be base64-encoded value' %
                                 self.friendly_name(cfg)) from err

            try:
                digest = base64.b64decode(value['digest'])
            except (KeyError, binascii.Error) as err:
                raise ValueError('%s: invalid digest: digest must be base64-encoded value' %
                                 self.friendly_name(cfg)) from err

            return DigestValue(salt, digest, self.algorithm)

        if isinstance(value, str):
            return self._hash(value)

        raise ValueError('%s: invalid salt-digest tuple' % self.friendly_name(cfg))


class SecureField(Field):
    '''
    A secure storage field where the plaintext configuration value is encrypted on disk and
    decrypted in memory when the configuration file is loaded.
    '''
    storage_type = str

    def __init__(self, method: str = 'best', sensitive: bool = True, **kwargs):
        '''
        :param method: encryption method, see
            :meth:`~cincoconfig.KeyFile._get_provider`
        '''
        super().__init__(sensitive=sensitive, **kwargs)
        self.method = method

    def to_basic(self, cfg: BaseConfig, value: str) -> Optional[dict]:
        if not value:
            return None

        with cfg._keyfile as ctx:
            secret = ctx.encrypt(value, method=self.method)

        return {
            'method': secret.method,
            'ciphertext': base64.b64encode(secret.ciphertext).decode()
        }

    def to_python(self, cfg: BaseConfig, value: Any) -> Optional[str]:
        if value is None:
            return value

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            method = value.get('method')
            ciphertext_b64 = value.get('ciphertext')

            if not method:
                raise ValueError('%s: no encryption method specified' % self.friendly_name(cfg))

            if not isinstance(ciphertext_b64, str):
                raise ValueError('%s: invalid ciphertext' % self.friendly_name(cfg))

            try:
                ciphertext = base64.b64decode(ciphertext_b64)
            except binascii.Error as err:
                raise ValueError('%s: invalid ciphertext' % self.friendly_name(cfg)) from err

            try:
                with cfg._keyfile as ctx:
                    text = ctx.decrypt(SecureValue(method, ciphertext))
            except (TypeError, EncryptionError) as err:
                raise ValueError('%s: decryption failed: %s' %
                                 (self.friendly_name(cfg), str(err))) from err
            else:
                return text.decode()

        raise ValueError('%s: invalid encrypted value' % self.friendly_name(cfg))


class BytesField(Field):
    '''
    Store binary data in an encoded string.
    '''
    storage_type = bytes
    #: Available encodings: base64 and hex
    ENCODINGS = ('base64', 'hex')

    def __init__(self, encoding: str = 'base64', **kwargs):
        '''
        :param encoding: binary data encoding, must be one of :attr:`ENCODINGS`
        '''
        super().__init__(**kwargs)

        if encoding not in BytesField.ENCODINGS:
            raise TypeError('invalid encoding: %s' % encoding)
        self.encoding = encoding

    def _validate(self, cfg: BaseConfig, value: Any) -> bytes:
        if isinstance(value, str):
            return value.encode()

        if isinstance(value, bytes):
            return value

        raise ValueError('value must be bytes, not %s' % type(value).__name__)

    def to_basic(self, cfg: BaseConfig, value: bytes) -> str:
        '''
        :returns: the encoded binary data
        '''
        if value is None:
            return value

        if self.encoding == 'base64':
            return base64.b64encode(value).decode()

        if self.encoding == 'hex':
            return value.hex()

        raise TypeError('%s: invalid encoding: %s' % (self.friendly_name(cfg), self.encoding))

    def to_python(self, cfg: BaseConfig, value: Any) -> Optional[bytes]:
        '''
        :returns: the decoded binary data
        '''
        if value is None:
            return value

        if not isinstance(value, str):
            raise ValueError('%s: value is not a string' % self.friendly_name(cfg))

        if self.encoding == 'base64':
            try:
                ret = base64.b64decode(value)
            except binascii.Error as err:
                raise ValueError('%s: invalid base64 encoding' % self.friendly_name(cfg)) from err
            else:
                return ret

        if self.encoding == 'hex':
            try:
                ret = bytes.fromhex(value)
            except ValueError as err:
                raise ValueError('%s: invalid hex encoding' % self.friendly_name(cfg)) from err
            else:
                return ret

        raise TypeError('%s: invalid encoding: %s' % (self.friendly_name(cfg), self.encoding))


class IncludeField(FilenameField):
    '''
    A special field that can include another configuration file when loading from disk. Included
    files are in the same scope as where the include field is defined for example:

    .. code-block:: yaml

        # file1.yaml
        db:
          include: "db.yaml"
        include: "core.yaml"

        # db.yaml
        host: "0.0.0.0"
        port: 27017

        # core.yaml
        mode: "production"
        ssl: true

    The final parsed configuration would be equivalent to:

    .. code-block:: yaml

        db:
          host: "0.0.0.0"
          port: 27017

        mode: "production"
        ssl: true

    Included files must be in the same configuration file format as their parent file. So,
    if the base configuration file is stored in JSON then every included file must also be in JSON.

    Cincoconfig does not track which configuration file set which field(s). When a config file is
    saved back to disk, it will be the entire configuration, even if it was originally defined
    across multiple included files.
    '''

    def __init__(self, startdir: str = None, **kwargs):
        '''
        :param startdir: resolve relative include paths to a start directory
        '''
        super().__init__(exists='file', startdir=startdir, **kwargs)

    def include(self, config: BaseConfig, fmt: ConfigFormat, filename: str, base: dict) -> dict:
        '''
        Include a configuration file and combine it with an already parsed basic value tree. Values
        defined in the included file will overwrite values in the base tree. Nested trees (``dict``
        objects) will be combined using a :meth:`dict.update` like method, :meth:`combine_trees`.

        :param config: configuration object
        :param fmt: configuration file format that will parse the included file
        :param filename: included file path
        :param base: base config value tree
        :returns: the new basic value tree containing the base tree and the included tree
        '''
        filename = self.validate(config, filename)
        with open(filename, 'rb') as fp:
            content = fp.read()

        child = fmt.loads(config, content)
        return self.combine_trees(base, child)

    def combine_trees(self, base: dict, child: dict) -> dict:
        '''
        An extension to :meth:`dict.update` but properly handles nested `dict` objects.

        :param base: base tree to extend
        :param child: child tree to apply onto base
        :returns: the new combined ``dict``
        '''
        ret = dict(base)
        for key, value in child.items():
            if key in base:
                base_value = base[key]
                if isinstance(base_value, dict) and isinstance(value, dict):
                    ret[key] = self.combine_trees(base_value, value)
                else:
                    ret[key] = value
            else:
                ret[key] = value

        return ret
