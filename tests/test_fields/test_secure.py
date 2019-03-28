#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import json
import hashlib
import base64
from unittest.mock import patch, mock_open
import pytest
from Crypto.Cipher import AES
from cincoconfig.fields import SecureField

SECRET = b'B' * 512
AESKEY = b'B' * 32
XORKEY = b'B' * 4096

KEY_FILE_CONTENTS = json.dumps({
    "secret": base64.b64encode(SECRET).decode(),
    "aes256": base64.b64encode(AESKEY).decode(),
    "xor": base64.b64encode(XORKEY).decode()
})

SECURE_IV = b"B" * AES.block_size
SECURE_SALT = b"B"
B64_SALT = base64.b64encode(SECURE_SALT).decode()

SECURE_VAL = "password"

SECURE_VAL_SHA1 = "{}:{}".format(
    B64_SALT,
    hashlib.sha1(SECURE_SALT + SECURE_VAL.encode() + SECRET).hexdigest()
)
SECURE_VAL_MD5 = "{}:{}".format(
    B64_SALT,
    hashlib.md5(SECURE_SALT + SECURE_VAL.encode() + SECRET).hexdigest()
)
SECURE_VAL_SHA224 = "{}:{}".format(
    B64_SALT,
    hashlib.sha224(SECURE_SALT + SECURE_VAL.encode() + SECRET).hexdigest()
)
SECURE_VAL_SHA256 = "{}:{}".format(
    B64_SALT,
    hashlib.sha256(SECURE_SALT + SECURE_VAL.encode() + SECRET).hexdigest()
)
SECURE_VAL_SHA384 = "{}:{}".format(
    B64_SALT,
    hashlib.sha384(SECURE_SALT + SECURE_VAL.encode() + SECRET).hexdigest()
)
SECURE_VAL_SHA512 = "{}:{}".format(
    B64_SALT,
    hashlib.sha512(SECURE_SALT + SECURE_VAL.encode() + SECRET).hexdigest()
)


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

    @patch("os.path.isfile", return_value=False)
    @patch("os.path.exists", return_value=False)
    def test_key_file_not_found(self, _mock_exists, _mock_isfile):
        with pytest.raises(FileNotFoundError):
            field = SecureField(key_path="/ferp/merp/.cincokey", key_exists=True)

    @patch("os.path.isfile", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_key_file_exists(self, _mock_exists, _mock_isfile):
        with pytest.raises(FileExistsError):
            field = SecureField(key_path="/ferp/merp/.cincokey", key_exists=False)

    @patch('os.urandom', return_value=SECURE_SALT)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_default_hash(self, _mock_file, _mock_urandom):
        field = SecureField(action="hash_sha1", default="password")
        field.__setdefault__(self.cfg)
        print(field.__getval__(self.cfg))
        print(SECURE_VAL_SHA1)
        assert field.__getval__(self.cfg) == SECURE_VAL_SHA1
