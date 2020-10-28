#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import os
from itertools import cycle
from typing import NamedTuple, Optional, Union, Tuple

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend
except ImportError:  # pragma: no cover
    AES_AVAILABLE = False
else:
    #: AES is available (``cryptography`` is installed)
    AES_AVAILABLE = True


#:
#: An encrypted value tuple containing the encryption method and the ciphertext.
#:
#: .. py:attribute:: method
#:
#:  the encryption method (:class:`str`)
#:
#: .. py:attribute:: ciphertext
#:
#:  the encrypted value (:class:`bytes`)
#:
SecureValue = NamedTuple('SecureValue', [('method', str), ('ciphertext', bytes)])


class EncryptionError(Exception):
    '''
    Exception raised whenever an error occurs during a encryption operation.
    '''


class IEncryptionProvider:
    '''
    Interface class for an encryption algorithm provider. An encryption provider
    implementes both encryption and decryption of string values.

    The encrypt and decrypt methods must be deterministic.

    .. code-block:: python

        b'message' == provider.decrypt(provider.decrypt(b'message'))

    The constructor for subclasses will receive a single argument: the encryption key.
    '''

    def encrypt(self, text: bytes) -> bytes:
        '''
        Encrypt a value.

        :param text: plain text value to encrypt
        :returns: encrypted value
        '''
        raise NotImplementedError()

    def decrypt(self, ciphertext: bytes) -> bytes:
        '''
        Decrypt a value.

        :param ciphertext: encrypted value to decrypt
        :returns: decrypted value
        '''
        raise NotImplementedError()


class KeyFile:
    '''
    The cincoconfig key file, containing a randomly generated 32 byte encryption key. The cinco
    key file is used by :class:`~cincoconfig.SecureField` to encrypt and decrypt values as
    they are written to and read from the configuration file.

    The keyfile is loaded as needed by using this class as a context manager. The key has an
    internal reference count and is only freed once the reference count is 0 (all context managers
    exited). THe key is cached internally so that the keyfile only has to be open and read once
    per configuration load or save.

    To encrypt a value:

    .. code-block:: python

        with keyfile as ctx:
            secret = ctx.encrypt(method='xor', text='hello, world')
    '''

    def __init__(self, filename: str):
        '''
        :param filename: the cinco key filename
        '''
        self.filename = filename
        self.__key = None  # type: Optional[bytes]
        self.__refcount = 0

    def __load_key(self) -> None:
        '''
        INTERNAL METHOD. Load configuration key.
        '''
        try:
            with open(self.filename, 'rb') as fp:
                self.__key = fp.read()
        except OSError:
            self.__key = self.__generate_key()
        else:
            self._validate_key()

    def __generate_key(self) -> bytes:
        '''
        Generate a random 32 byte key and save it to ``filename``.

        :returns: the generated key
        '''
        key = os.urandom(32)
        with open(self.filename, 'wb') as fp:
            fp.write(key)
        return key

    def generate_key(self) -> None:
        '''
        Generate a random 32 byte key and save it to ``filename``.
        '''
        # We generate the key but don't return the value in the public API so that we don't leak
        # the key outside of a with context.
        self.__generate_key()

    def _validate_key(self) -> None:
        '''
        Validate the key.

        :raises EncryptionError: invalid key
        '''
        if not self.__key or len(self.__key) != 32:
            raise EncryptionError('invalid encryption key file: %s' % self.filename)

    def __enter__(self) -> 'KeyFile':
        if not self.__key:
            self.__load_key()

        self.__refcount += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__refcount -= 1
        if self.__refcount == 0:
            self.__key = None

        return False

    def _get_provider(self, method: str) -> Tuple[IEncryptionProvider, str]:
        '''
        Get the encryption provider. ``method`` must be one of

        - ``aes`` - returns :class:`AesProvider`
        - ``xor`` - returns :class:`XorProvider`
        - ``best`` - returns the best available encryption provider: :class:`AesProvider` if AES
          encryption is available (``cryptography`` is installed), :class:`XorProvider` if AES
          is not available

        The resolved method is returned. For example, if ``best`` if specified, the best encryption
        method will be resolved and returned.

        The return value is a tuple of encryption provider instance and the resolved method.

        :returns: a tuple of ``(provider, method)``
        '''
        if not self.__key:
            raise TypeError('keyfile is not open')

        if method == 'aes' or (method == 'best' and AES_AVAILABLE):
            return AesProvider(self.__key), 'aes'
        if method in ('xor', 'best'):
            return XorProvider(self.__key), 'xor'
        raise TypeError('invalid encryption method: %s' % method)

    def encrypt(self, text: Union[str, bytes], method: str = 'best') -> SecureValue:
        '''
        :param text: plaintext to encrypt
        :param method: encryption method to use
        :returns: the encrypted value
        '''
        if not self.__key:
            raise TypeError('key file is not open')

        bindata = text.encode() if isinstance(text, str) else text

        provider, method = self._get_provider(method)
        ciphertext = provider.encrypt(bindata)
        return SecureValue(method, ciphertext)

    def decrypt(self, secret: SecureValue) -> bytes:
        '''
        :param secret: encrypted value
        :returns: decrypted value
        '''
        if not self.__key:
            raise TypeError('key file is not open')

        provider, _ = self._get_provider(secret.method)
        return provider.decrypt(secret.ciphertext)


class XorProvider(IEncryptionProvider):
    '''
    XOR-bitwise "encryption". The XOR provider should only be used to obfuscate, not encrypt, a
    value since XOR operations can be easily reversed.
    '''

    def __init__(self, key: bytes):
        self.__key = key

    def encrypt(self, text: Union[str, bytes]) -> bytes:
        '''
        :returns: the encrypted value
        '''
        bindata = text.encode() if isinstance(text, str) else text
        buff = bytearray(bindata)
        for i, c in zip(range(len(buff)), cycle(self.__key)):
            buff[i] ^= c
        return bytes(buff)

    def decrypt(self, ciphertext: bytes) -> bytes:
        '''
        :returns: the decrypted values
        '''
        return self.encrypt(ciphertext)


class AesProvider(IEncryptionProvider):
    '''
    AES-256 encryption provider. This class requires the ``cryptography`` library. Each encrypted
    value has a randomly generated 16-byte IV.
    '''

    def __init__(self, key: bytes):
        if not AES_AVAILABLE:
            raise TypeError('AES encryption is not available; please install cryptography')
        self.__key = key

    def decrypt(self, ciphertext: bytes) -> bytes:
        '''
        :returns: the plaintext value
        '''
        if not ciphertext or len(ciphertext) < 32:
            raise EncryptionError('invalid initialization vector')

        iv = ciphertext[:16]
        ciphertext = ciphertext[16:]
        cipher = Cipher(algorithms.AES(self.__key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        unpadder = padding.PKCS7(128).unpadder()
        text = decryptor.update(ciphertext) + decryptor.finalize()

        return unpadder.update(text) + unpadder.finalize()

    def encrypt(self, text: bytes) -> bytes:
        '''
        :returns: the encrypted value
        '''
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.__key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()

        padded = padder.update(text) + padder.finalize()
        return iv + encryptor.update(padded) + encryptor.finalize()
