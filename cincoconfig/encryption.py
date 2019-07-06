#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import os
from itertools import cycle
from typing import AnyStr, NamedTuple

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend
except ImportError:  # pragma: no cover
    AES_AVAILABLE = False
else:
    AES_AVAILABLE = True


SecureValue = NamedTuple('SecureValue', [
    ('method', str),
    ('ciphertext', bytes)
])


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
    Wrapper around the cincoconfig encryption key file.
    '''

    def __init__(self, filename: str):
        self.filename = filename
        self.__key = None  # type: bytes
        self.__refcount = 0

    def __load_key(self) -> None:
        try:
            with open(self.filename, 'rb') as fp:
                self.__key = fp.read()
        except OSError:
            self.generate_key()
        else:
            self._validate_key()

    def generate_key(self) -> None:
        key = os.urandom(32)
        with open(self.filename, 'wb') as fp:
            fp.write(key)
        self.__key = key

    def _validate_key(self) -> None:
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

    def _get_provider(self, method: str) -> IEncryptionProvider:
        if method == 'aes':
            return AesProvider(self.__key)
        elif method == 'xor':
            return XorProvider(self.__key)
        raise TypeError('invalid encryption method: %s' % method)

    def encrypt(self, text: AnyStr, method: str = 'best') -> SecureValue:
        if not self.__key:
            raise TypeError('key file is not open')

        if method == 'best':
            method = 'aes' if AES_AVAILABLE else 'xor'

        if isinstance(text, str):
            text = text.encode()

        provider = self._get_provider(method)
        ciphertext = provider.encrypt(text)
        return SecureValue(method, ciphertext)

    def decrypt(self, secret: SecureValue) -> str:
        if not self.__key:
            raise TypeError('key file is not open')

        provider = self._get_provider(secret.method)
        return provider.decrypt(secret.ciphertext).decode()


class XorProvider(IEncryptionProvider):

    def __init__(self, key: bytes):
        self.__key = key

    def encrypt(self, value: bytes) -> bytes:
        buff = bytearray(value)
        for i, c in zip(range(len(buff)), cycle(self.__key)):
            buff[i] ^= c
        return bytes(buff)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return self.encrypt(ciphertext)


class AesProvider(IEncryptionProvider):

    def __init__(self, key: bytes):
        if not AES_AVAILABLE:
            raise TypeError('AES encryption is not available; please install cryptography')
        self.__key = key

    def decrypt(self, ciphertext: bytes) -> bytes:
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
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.__key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()

        padded = padder.update(text) + padder.finalize()
        return iv + encryptor.update(padded) + encryptor.finalize()
