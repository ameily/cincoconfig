#
# Copyright (C) 2019 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import base64
from unittest.mock import MagicMock
import pytest
from cincoconfig.fields import SecureField
from cincoconfig.encryption import SecureValue, EncryptionError


class StubKeyFile:

    def __init__(self):
        StubKeyFile.__enter__ = MagicMock(return_value=self)
        StubKeyFile.__exit__ = MagicMock()
        self.encrypt = MagicMock(return_value=SecureValue('test', b'ciphertext'))
        self.decrypt = MagicMock(return_value=b'plaintext')


class StubConfig:

    def __init__(self):
        self._keyfile = StubKeyFile()


class TestSecureField:

    def test_to_basic_none(self):
        field = SecureField()
        assert field.to_basic(None, None) is None

    def test_to_basic(self):
        cfg = StubConfig()
        field = SecureField(method='test')
        assert field.to_basic(cfg, 'hello') == {
            'method': 'test',
            'ciphertext': base64.b64encode(b'ciphertext').decode()
        }
        cfg._keyfile.__enter__.assert_called_once()
        cfg._keyfile.encrypt.assert_called_once_with('hello', method='test')
        cfg._keyfile.__exit__.assert_called_once_with(None, None, None)

    def test_to_python_none(self):
        field = SecureField()
        assert field.to_python(None, None) is None

    def test_to_python_str(self):
        field = SecureField()
        assert field.to_python(None, 'hello') == 'hello'

    def test_to_python_dict_invalid_method(self):
        field = SecureField(name='asdf')
        with pytest.raises(ValueError):
            field.to_python(None, {
                'method': None,
                'ciphertext': b'hello'
            })

    def test_to_python_dict_invalid_ciphertext_base64(self):
        field = SecureField(name='asdf')
        with pytest.raises(ValueError):
            field.to_python(None, {
                'method': 'xor',
                'ciphertext': 'hello'
            })

    def test_to_python_dict_invalid_ciphertext(self):
        cfg = StubConfig()
        field = SecureField(name='asdf')
        cfg._keyfile.decrypt.side_effect = EncryptionError()
        cfg._keyfile.__exit__.return_value = False

        with pytest.raises(ValueError):
            field.to_python(cfg, {
                'method': 'test',
                'ciphertext': 'aGVsbG8='
            })

        cfg._keyfile.decrypt.assert_called_once_with(SecureValue('test', b'hello'))

    def test_to_python_dict_invalid_ciphertext_int(self):
        cfg = StubConfig()
        field = SecureField(name='asdf')
        cfg._keyfile.decrypt.side_effect = EncryptionError()
        cfg._keyfile.__exit__.return_value = False

        with pytest.raises(ValueError):
            field.to_python(cfg, {
                'method': 'test',
                'ciphertext': 10
            })

    def test_to_python_dict_valid(self):
        cfg = StubConfig()
        field = SecureField(name='asdf')

        assert field.to_python(cfg, {
            'method': 'test',
            'ciphertext': 'aGVsbG8='
        }) == 'plaintext'

    def test_to_python_invalid_type(self):
        field = SecureField()
        with pytest.raises(ValueError):
            field.to_python(None, 100)



'''
import json
import hashlib
import base64
import random
from unittest.mock import patch, mock_open
import pytest
from Crypto.Cipher import AES
from cincoconfig.fields import SecureField

SECRET = b'B' * 512
AESKEY = b'B' * 32
XORKEY = b'B' * 4096

KEY_DICT = {
    "aes256": base64.b64encode(AESKEY).decode(),
    "xor": base64.b64encode(XORKEY).decode(),
    "secret": base64.b64encode(SECRET).decode()
}

KEY_FILE_CONTENTS = json.dumps(KEY_DICT)

SECURE_IV = b"B" * AES.block_size
SECURE_SALT = b"B"
SECURE_SEED = b"B" * 64
B64_SEED = base64.b64encode(SECURE_SEED).decode()
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


def aes_encrypt():
    key = base64.b64decode(KEY_DICT["aes256"].encode())
    obj = AES.new(key, AES.MODE_CFB, SECURE_IV)
    ciphertext = obj.encrypt(SECURE_VAL.encode())
    return base64.b64encode(SECURE_IV + ciphertext).decode()


SECURE_VAL_AES = aes_encrypt()


def xor_encrypt():
    key = base64.b64decode(KEY_DICT["xor"].encode())
    random.seed(SECURE_SEED)
    ciphertext = b''
    for clear_char in SECURE_VAL:
        ciphertext += bytes([(ord(clear_char) ^ key[random.randint(0, len(key) - 1)])])
    b64ciphertext = base64.b64encode(ciphertext).decode()
    b64seed = base64.b64encode(SECURE_SEED).decode()
    return "{}:{}".format(b64seed, b64ciphertext)


SECURE_VAL_XOR = xor_encrypt()


class MockConfig:

    def __init__(self):
        self._data = {}

    def __getitem__(self, key):
        return self._data[key]


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
            SecureField(key_path="/ferp/merp/.cincokey", key_exists=True)

    @patch("os.path.isfile", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_key_file_exists(self, _mock_exists, _mock_isfile):
        with pytest.raises(FileExistsError):
            SecureField(key_path="/ferp/merp/.cincokey", key_exists=False)

    @patch('os.urandom', return_value=SECURE_SALT)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_default_hash(self, _mock_file, _mock_urandom):
        field = SecureField(action="hash_sha1", default=SECURE_VAL)
        field.__setdefault__(self.cfg)
        assert field.__getval__(self.cfg) == SECURE_VAL_SHA1
        assert field.check_hash(self.cfg, SECURE_VAL) is True

    @patch('os.urandom', return_value=SECURE_SALT)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_hash_convertion(self, _mock_file, _mock_urandom):
        expected = {
            "type": "secure_value",
            "value": SECURE_VAL_MD5
        }

        md5 = SecureField(action="hash_md5", default=SECURE_VAL)
        md5.__setdefault__(self.cfg)
        assert md5.to_basic(self.cfg, self.cfg._data[md5.key]) == expected
        assert md5.to_basic(self.cfg, None) is None
        assert md5.to_python(self.cfg, expected) == SECURE_VAL_MD5
        assert md5.to_python(self.cfg, None) is None
        assert md5.to_python(self.cfg, SECURE_VAL) == SECURE_VAL_MD5

        md5._action = "im doing it wrong"
        with pytest.raises(TypeError):
            md5.to_python(self.cfg, self.cfg._data[md5.key])

        with pytest.raises(TypeError):
            md5.to_python(self.cfg, expected)

        with pytest.raises(ValueError):
            md5.to_python(self.cfg, [])

    @patch('os.urandom', return_value=SECURE_SEED)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_enc_convertion(self, _mock_file, _mock_urandom):
        expected = {
            "type": "secure_value",
            "value": SECURE_VAL_XOR
        }

        xor = SecureField(action="enc_xor", default=SECURE_VAL)
        xor.__setdefault__(self.cfg)
        assert xor.to_basic(self.cfg, SECURE_VAL) == expected
        assert xor.to_python(self.cfg, expected) == SECURE_VAL
        assert self.cfg._data[xor.key] == SECURE_VAL_XOR
        assert xor.to_python(self.cfg, SECURE_VAL) == SECURE_VAL
        assert self.cfg._data[xor.key] == SECURE_VAL_XOR

    @patch('os.urandom', return_value=SECURE_SALT)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_hash_md5(self, _mock_file, _mock_urandom):
        md5 = SecureField(action="hash_md5")
        md5.__setdefault__(self.cfg)

        with pytest.raises(ValueError):
            md5.check_hash(self.cfg, SECURE_VAL)

        md5.__setval__(self.cfg, SECURE_VAL)
        assert md5.__getval__(self.cfg) == SECURE_VAL_MD5
        assert md5._validate(self.cfg, self.cfg._data[md5.key]) == SECURE_VAL_MD5
        assert md5._validate(self.cfg, None) is None

    @patch('os.urandom', return_value=SECURE_SALT)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_hash_sha1(self, _mock_file, _mock_urandom):
        sha1 = SecureField(action="hash_sha1")
        sha1.__setdefault__(self.cfg)
        sha1.__setval__(self.cfg, SECURE_VAL)
        assert sha1.__getval__(self.cfg) == SECURE_VAL_SHA1

    @patch('os.urandom', return_value=SECURE_SALT)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_hash_sha224(self, _mock_file, _mock_urandom):
        sha224 = SecureField(action="hash_sha224")
        sha224.__setdefault__(self.cfg)
        sha224.__setval__(self.cfg, SECURE_VAL)
        assert sha224.__getval__(self.cfg) == SECURE_VAL_SHA224

    @patch('os.urandom', return_value=SECURE_SALT)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_hash_sha256(self, _mock_file, _mock_urandom):
        sha256 = SecureField(action="hash_sha256")
        sha256.__setdefault__(self.cfg)
        sha256.__setval__(self.cfg, SECURE_VAL)
        assert sha256.__getval__(self.cfg) == SECURE_VAL_SHA256

    @patch('os.urandom', return_value=SECURE_SALT)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_hash_sha384(self, _mock_file, _mock_urandom):
        sha384 = SecureField(action="hash_sha384")
        sha384.__setdefault__(self.cfg)
        sha384.__setval__(self.cfg, SECURE_VAL)
        assert sha384.__getval__(self.cfg) == SECURE_VAL_SHA384

    @patch('os.urandom', return_value=SECURE_SALT)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_hash_sha512(self, _mock_file, _mock_urandom):
        sha512 = SecureField(action="hash_sha512")
        sha512.__setdefault__(self.cfg)
        sha512.__setval__(self.cfg, SECURE_VAL)
        assert sha512.__getval__(self.cfg) == SECURE_VAL_SHA512

    @patch('os.urandom', return_value=SECURE_SEED)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_default_any_enc(self, _mock_file, _mock_urandom):
        xor = SecureField(action="enc_xor", default=SECURE_VAL)
        xor.__setdefault__(self.cfg)
        assert xor.__getval__(self.cfg) == SECURE_VAL
        assert self.cfg._data[xor.key] == SECURE_VAL_XOR

    @patch('os.urandom', return_value=SECURE_SEED)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_xor(self, _mock_file, _mock_urandom):
        xor = SecureField(action="enc_xor")
        xor.__setdefault__(self.cfg)
        xor.__setval__(self.cfg, SECURE_VAL)
        assert xor.__getval__(self.cfg) == SECURE_VAL
        assert self.cfg._data[xor.key] == SECURE_VAL_XOR

    @patch('os.urandom', return_value=SECURE_IV)
    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_aes(self, _mock_file, _mock_urandom):
        aes = SecureField(action="enc_aes256")
        aes.__setdefault__(self.cfg)
        assert aes.__getval__(self.cfg) is None
        aes.__setval__(self.cfg, SECURE_VAL)
        assert aes.__getval__(self.cfg) == SECURE_VAL
        assert self.cfg._data[aes.key] == SECURE_VAL_AES

    @patch("os.urandom", side_effect=[AESKEY, XORKEY, SECRET])
    @patch("os.path.isfile", return_value=False)
    @patch("os.path.exists", return_value=False)
    @patch('builtins.open', new_callable=mock_open)
    def test_generate_key_file(self, mock_file, _mock_exists, _mock_isfile, _mock_urandom):
        SecureField()
        handle = mock_file()
        handle.write.assert_called_once_with(KEY_FILE_CONTENTS)

    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_invalid_action_validate(self, _mock_file):
        with pytest.raises(TypeError):
            xor = SecureField(action="enc_xor")
            xor.__setdefault__(self.cfg)
            xor._action = "im doing it wrong"
            xor.__setval__(self.cfg, SECURE_VAL)

    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_invalid_action_encrypt(self, _mock_file):
        with pytest.raises(TypeError):
            xor = SecureField(action="enc_xor")
            xor.__setdefault__(self.cfg)
            xor._action = "im doing it wrong"
            xor._encrypt(SECURE_VAL)

    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_invalid_action_decrypt(self, _mock_file):
        with pytest.raises(TypeError):
            xor = SecureField(action="enc_xor")
            xor.__setdefault__(self.cfg)
            xor.__setval__(self.cfg, SECURE_VAL)
            xor._action = "im doing it wrong"
            xor._decrypt(self.cfg._data[xor.key])

    @patch('builtins.open', new_callable=mock_open, read_data=KEY_FILE_CONTENTS)
    def test_invalid_action_hash(self, _mock_file):
        with pytest.raises(TypeError):
            field = SecureField(default="blah")
            field.__setdefault__(self.cfg)
            field._action = "im doing it wrong"
            field._hash_value(self.cfg._data[field.key], b'B')
'''
