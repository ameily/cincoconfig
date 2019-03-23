#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import hashlib
import pytest
from Crypto.Cipher import AES
from cincoconfig.fields import SecureField

SECURE_KEY = b"B" * 32
SECURE_IV = b"B" * AES.block_size
SECURE_VAL = "password"
SECURE_VAL_SHA1 = hashlib.sha1(SECURE_VAL.encode()).hexdigest()
SECURE_VAL_MD5 = hashlib.md5(SECURE_VAL.encode()).hexdigest()
SECURE_VAL_SHA224 = hashlib.sha224(SECURE_VAL.encode()).hexdigest()
SECURE_VAL_SHA256 = hashlib.sha256(SECURE_VAL.encode()).hexdigest()
SECURE_VAL_SHA384 = hashlib.sha384(SECURE_VAL.encode()).hexdigest()
SECURE_VAL_SHA512 = hashlib.sha512(SECURE_VAL.encode()).hexdigest()


class MockConfig:

    def __init__(self):
        self._data = {}

    def __getitem__(self, key):
        return self._data[key]


class MockSchema:

    def __init__(self):
        self._fields = {}

    def _add_field(self, name, field):
        self._fields[name] = field
        field.__setkey__(self, name)


class TestSecureField:

    def setup_method(self, method=None):
        self.cfg = MockConfig()

    def test_invalid_action(self):
        with pytest.raises(TypeError):
            field = SecureField(action="asdf")

    def test_default_action(self):
        field = SecureField()
        assert field._action == "hash_sha256"

    def test_helper_hash(self):
        hashed = SecureField.hash(SECURE_VAL, "hash_sha512")
        assert hashed == SECURE_VAL_SHA512

    def test_helper_invalid_action(self):
        with pytest.raises(TypeError):
            hashed = SecureField.hash(SECURE_VAL, "ferp")

    def test_default_hash(self):
        field = SecureField(action="hash_sha1", default="password")
        field.__setdefault__(self.cfg)
        assert field.__getval__(self.cfg) == SECURE_VAL_SHA1
