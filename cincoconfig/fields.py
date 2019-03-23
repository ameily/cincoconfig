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
           'LogLevelField', 'SecureField')


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


class SecureField(Field):
    '''
    A field that will be encrypted/hashed when written to or read from disk

    The purpose of this field is to provide a method to store sensitive information
    in config file(s) in a way that does not leak that information to those who can
    read the config file(s). A ``SecureField`` can either be encrypted or hashed.
    Using encryption has the benefit of providing access to the clear-text value in
    code. Using a hash on the other hand is more secure because there is no way
    to get the clear-text data back after it has been hashed.

    For example, if your application requires a password to be stored in the
    config that is used to automatically authenticate with another service, the
    value should be encrypted so that the password can be recovered when needed.
    Alternatively, if your application stores a user's credentials to authenticate
    them with your service, it should be stored hashed and that hash should be compared
    to the hash of the value submitted by a user for authentication.

    When written to a config file, a ``SecureField`` is stored as a dict, for example:

    .. code-block:: json

        "password": {
            "value": "+QR/5ZV8XDes52YNoE624UyHcQNtQPQC",
            "type": "secure_value"
        }

    The above is an example of an encrypted value. This password was encrypted using
    AES256 and the resulting ciphertext is base64 encoded so it can be written as text.

    When a ``SecureField`` is read from a config, it is expected to be in either string
    or dict form. In dict form, it is assumed that the value has not been modified, meaning
    encrypted values are encrypted and hashed values are hashed. In string form the value
    is assumed to be clear-text and in need of securing (e.g. hashing or encryption).

    Consider the following config file:

    .. code-block:: json

        "password": "mySecretPassword"

    If *password* is defined in the schema as a ``SecureField``, when this value is read,
    the system will know it needs to be secured due to the lack of *type* information (e.g.
    it's not a dict with ``type: "secure_value"``). If the secure **action** is a hashing
    algorithm, the value will be hashed and next time ``Config.save`` is called, the value
    for password will be overwritten:

    .. code-block:: json

        "password": {
            "value": <hash_of_mySecretPassword>
            "type": "secure_value"
        }

    If a ``SecureField`` is modified in a config file manually, the user must ensure
    they set the value to a string so the system recognizes that the field needs to be
    re-secured. If the dict is modified in place, the system will fail to properly secure
    the value.

    For encryption, ``SecureField`` will generate a *.cincokey* file in the current user's
    home directory if one has not already been generated. Cinco config will handle key
    management automatically. Encryption within CinoConfig is all "best-effort", meaning
    it will not protect passwords or data from people who have full access to the system
    running the application. If a user has access to read the *.cincokey* file, all the
    secure fields could be exposed to that user. The goal here is to secure the config
    file against accidental leaks or application vulnerabilities that expose the config
    file itself.

    When using a ``SecureField`` in code it's important to remember that encryption
    and hashing will happen automatically and transparently. Never set the value
    of the field to encrypted or hashed data unless you want that data hashed/encrypted
    again.

    .. code-block:: python

        >>> import json
        >>> from cincoconfig import *
        >>> cfg = Schema()
        >>> cfg.password = SecureField(action="enc_aes256", default="P@55w0rd")
        >>> cfg.hash = SecureField(action="hash_md5", default="P@55w0rd")
        >>> config = cfg()
        >>> config.password
        'P@55w0rd'
        >>> config.hash
        '37e4392dad1ad3d86680a8c6b06ede92'
        >>> print(json.dumps(config.to_tree(), indent=4))
        {
            "hash": {
                "value": "37e4392dad1ad3d86680a8c6b06ede92",
                "type": "secure_value"
            },
            "password": {
                "value": "nf5eOOHbgG2MPlxd2GhvnvH1C2RnNIHp",
                "type": "secure_value"
            }
        }
        >>>
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
        :raises TypeError: if the user specifies an invalid action or if the user attempts
            to use an action that requires a python library that is not installed
        '''
        super().__init__(**kwargs)
        self._action = action or 'hash_sha256'
        self.hashed = False  # Whether or not we've already hashed a value
        self._method = 'hash' if self._action in self.HASH_ACTION else 'enc'

        # Validate the action
        if self._action not in self.HASH_ACTION + self.ENC_ACTION:
            raise TypeError('action %s is not a valid hash or encryption action' % self._action)

        if self._method == 'enc' and self._action != 'enc_xor':
            # Need to make sure pycrypto is installed
            try:
                from Crypto.Cipher import AES  # pylint: disable=unused-import
            except ImportError:
                raise TypeError('action %s requires the pycrypto module' % self._action)

        if self._method == 'enc':
            # TODO: Generate/read/manage a key file
            self._generate_key_file()

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

        if self._action in self.HASH_ACTION:
            cfg._data[self.key] = self._hash(self.default)
        elif self._action in self.ENC_ACTION:
            cfg._data[self.key] = self._encrypt(self.default)

    def __getval__(self, cfg: Config) -> Any:
        '''
        Retrieve the value and decrypt it if it's not a hashed value

        :param cfg: current config
        :returns: decrypted value if possible
        '''
        if cfg._data[self.key] is None:
            return None

        if self._action in self.ENC_ACTION:
            return self._decrypt(cfg._data[self.key])

        return cfg._data[self.key]

    def _encrypt(self, value: str) -> str:
        '''
        Encrypt the value

        :param value: value to encrypt
        :returns: encrypted value
        :raises TypeError: if the action is not valid
        '''
        if self._action == "enc_aes256":
            from Crypto.Cipher import AES

            ivec = os.urandom(AES.block_size)

            # TODO: Use key from generated key file
            obj = AES.new(self._generate_key_file(), AES.MODE_CFB, ivec)
            ciphertext = obj.encrypt(value)
            return base64.b64encode(ivec + ciphertext).decode()
        if self._action == "enc_xor":
            return value  # TODO: implement XOR to support no-dependency encryption

        # TODO: Do I need to raise an exception? I check in __init__() that the
        # action is valid. Maybe self._action should be self._action to imply
        # private membership?
        raise TypeError('invalid encryption action %s' % self._action)

    def _decrypt(self, value: str) -> str:
        '''
        Decrypt the value

        :param value: value to decrypt
        :returns: decrypted value
        '''
        if self._action == "enc_aes256":
            from Crypto.Cipher import AES

            ciphertext = base64.b64decode(value.encode())
            ivec = ciphertext[:AES.block_size]
            ciphertext = ciphertext[AES.block_size:]

            # TODO: Use key from generated key file
            obj = AES.new(self._generate_key_file(must_exist=True), AES.MODE_CFB, ivec)
            return obj.decrypt(ciphertext).decode()
        if self._action == "enc_xor":
            return value  # TODO: implement XOR to support no-dependency encryption

        # TODO: Do I need to raise an exception? I check in __init__() that the
        # action is valid. Maybe self._action should be self._action to imply
        # private membership?
        raise TypeError('invalid encryption action %s' % self._action)

    @staticmethod
    def hash(value: str, action: str) -> str:
        '''
        Helper public method provided for easy hashing. This can be used
        to check if a provided clear-text password matches the hash for that
        password:

        .. code-block:: python

            >>> from cincoconfig import *
            >>> cfg = Schema()
            >>> cfg.password_hash = SecureField(action="hash_sha256")
            >>> config = cfg()
            >>> config.password_hash = "mySecretPassword"
            >>> config.password_hash
            '2250e74c6f823de9d70c2222802cd059dc970f56ed8d41d5d22d1a6d4a2ab66f'
            >>> config.password_hash == SecureField.hash("mySecretPassword", "hash_sha256")
            True
            >>>

        :param value: the value to be hashed
        :param action: the hash action
        :raise TypeError: if the action provided is invalid
        '''

        # TODO: Salt the hashes

        if action == "hash_md5":
            return hashlib.md5(value.encode()).hexdigest()
        if action == "hash_sha1":
            return hashlib.sha1(value.encode()).hexdigest()
        if action == "hash_sha224":
            return hashlib.sha224(value.encode()).hexdigest()
        if action == "hash_sha256":
            return hashlib.sha256(value.encode()).hexdigest()
        if action == "hash_sha384":
            return hashlib.sha384(value.encode()).hexdigest()
        if action == "hash_sha512":
            return hashlib.sha512(value.encode()).hexdigest()

        raise TypeError("action %s is not a valid hash action" % action)

    def _hash(self, value: str) -> str:  # pylint: disable=too-many-return-statements
        '''
        Private method used to hash a value only if it hasn't already been hashed.

        :param value: value to hash
        :returns: hashed value
        '''

        if self.hashed:
            return value

        self.hashed = True

        return self.hash(value, self._action)

    def _validate(self, cfg: Config, value: str) -> str:
        '''
        Validate a value.

        :param cfg: current Config
        :param value: value to validate
        '''
        if value is None:
            self.hashed = False
            return value

        if self._action in self.HASH_ACTION:
            if value != cfg._data[self.key]:
                # Only hash if the value has changed
                # to avoid hashing a hash
                self.hashed = False

            return self._hash(value)
        if self._action in self.ENC_ACTION:
            return self._encrypt(value)

        # TODO: Do I need to raise an exception? I check in __init__() that the
        # action is valid. Maybe self._action should be self._action to imply
        # private membership?
        raise TypeError("unknown action %s" % self._action)

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

        if self._action in self.ENC_ACTION:
            value = self._encrypt(value)
        if self._action in self.HASH_ACTION:
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
        :raises ValueError: if the value read from the config is neither a dict nor a string
        '''
        if value is None:
            return value

        if isinstance(value, dict) and value.get("type", "") == "secure_value":
            if self._action in self.HASH_ACTION:
                # It's a dict with type 'secure_value', we assume it's already hashed
                self.hashed = True

                # Set manually so we don't hash again in _validate()
                cfg._data[self.key] = value.get("value")

                return value.get("value")
            if self._action in self.ENC_ACTION:
                # It's a dict with type 'secure_value', we assume it's already encrypted
                return self._decrypt(value.get("value"))

            raise TypeError("unknown action %s" % self._action)

        if isinstance(value, str):
            if self._action in self.HASH_ACTION:
                # String value, assume it's not hashed. User-modified config
                self.hashed = False

                # Set manually so we don't hash again in _validate()
                cfg._data[self.key] = self._hash(value)

                return cfg._data[self.key]
            if self._action in self.ENC_ACTION:
                # String value, assume it's not encrypted but
                # don't encrypt here, it'll get encrypted in
                # _validate() when the value is set
                return value

            # TODO: Do I need to raise an exception? I check in __init__() that the
            # action is valid. Maybe self._action should be self._action to imply
            # private membership?
            raise TypeError("unknown action %s" % self._action)

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
