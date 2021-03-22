#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#
'''
Secure fields.
'''
import os
import hashlib
import base64
import binascii
from typing import Union, Any, Optional, Callable, NamedTuple, Dict

from ..core import Config, Field
from ..encryption import EncryptionError, SecureValue

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

        # Second time application executes
        >>> print(cfg.password)
        c2MPwSJw1QYMOcE2O+cVFA==:JSNbBj3wCgh7alFM7l0geg==

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

    def __setdefault__(self, cfg: Config) -> None:
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
        cfg._data[self._key] = val

    def _validate(self, cfg: Config, value: Any) -> DigestValue:
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

    def to_basic(self, cfg: Config, value: DigestValue) -> dict:
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

    def to_python(self, cfg: Config, value: Union[dict, str]) -> DigestValue:
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
                raise ValueError('invalid salt: salt must be base64-encoded value') from err

            try:
                digest = base64.b64decode(value['digest'])
            except (KeyError, binascii.Error) as err:
                raise ValueError('invalid digest: digest must be base64-encoded value') from err

            return DigestValue(salt, digest, self.algorithm)

        if isinstance(value, str):
            return self._hash(value)

        raise ValueError('invalid salt-digest tuple')


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

    def to_basic(self, cfg: Config, value: str) -> Optional[dict]:
        if not value:
            return None

        with cfg._keyfile as ctx:
            secret = ctx.encrypt(value, method=self.method)

        return {
            'method': secret.method,
            'ciphertext': base64.b64encode(secret.ciphertext).decode()
        }

    def to_python(self, cfg: Config, value: Any) -> Optional[str]:
        if value is None:
            return value

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            method = value.get('method')
            ciphertext_b64 = value.get('ciphertext')

            if not method:
                raise ValueError('no encryption method specified')

            if not isinstance(ciphertext_b64, str):
                raise ValueError('invalid ciphertext')

            try:
                ciphertext = base64.b64decode(ciphertext_b64)
            except binascii.Error as err:
                raise ValueError('invalid ciphertext') from err

            try:
                with cfg._keyfile as ctx:
                    text = ctx.decrypt(SecureValue(method, ciphertext))
            except (TypeError, EncryptionError) as err:
                raise ValueError('decryption failed: %s' % str(err)) from err
            else:
                return text.decode()

        raise ValueError('invalid encrypted value')
