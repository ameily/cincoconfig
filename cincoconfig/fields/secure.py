#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Cinco Config Secure Field.
'''

import os
import hashlib
import base64
from typing import Union, Any
from cincoconfig.abc import Field
from cincoconfig.config import Config


__all__ = ('SecureField',)


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
