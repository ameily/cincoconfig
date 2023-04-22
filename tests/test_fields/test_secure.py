#
# Copyright (C) 2021 Adam Meily
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
        self.encrypt = MagicMock(return_value=SecureValue("test", b"ciphertext"))
        self.decrypt = MagicMock(return_value=b"plaintext")


class StubConfig:
    def __init__(self):
        self._keyfile = StubKeyFile()
        self._parent = None
        self._key = None

    def _full_path(self):
        return ""


class TestSecureField:
    def test_to_basic_none(self):
        field = SecureField()
        assert field.to_basic(StubConfig(), None) is None

    def test_to_basic_empty_string(self):
        field = SecureField()
        assert field.to_basic(None, "") is None

    def test_to_basic(self):
        cfg = StubConfig()
        field = SecureField(method="test")
        assert field.to_basic(cfg, "hello") == {
            "method": "test",
            "ciphertext": base64.b64encode(b"ciphertext").decode(),
        }
        cfg._keyfile.__enter__.assert_called_once_with()
        cfg._keyfile.encrypt.assert_called_once_with("hello", method="test")
        cfg._keyfile.__exit__.assert_called_once_with(None, None, None)

    def test_to_python_none(self):
        field = SecureField()
        assert field.to_python(StubConfig(), None) is None

    def test_to_python_empty_string(self):
        field = SecureField()
        assert field.to_python(None, "") == ""

    def test_to_python_str(self):
        field = SecureField()
        assert field.to_python(StubConfig(), "hello") == "hello"

    def test_to_python_dict_invalid_method(self):
        field = SecureField(name="asdf")
        with pytest.raises(ValueError):
            field.to_python(StubConfig(), {"method": None, "ciphertext": b"hello"})

    def test_to_python_dict_invalid_ciphertext_base64(self):
        field = SecureField(name="asdf")
        with pytest.raises(ValueError):
            field.to_python(StubConfig(), {"method": "xor", "ciphertext": "hello"})

    def test_to_python_dict_invalid_ciphertext(self):
        cfg = StubConfig()
        field = SecureField(name="asdf")
        cfg._keyfile.decrypt.side_effect = EncryptionError()
        cfg._keyfile.__exit__.return_value = False

        with pytest.raises(ValueError):
            field.to_python(cfg, {"method": "test", "ciphertext": "aGVsbG8="})

        cfg._keyfile.decrypt.assert_called_once_with(SecureValue("test", b"hello"))

    def test_to_python_dict_invalid_ciphertext_int(self):
        cfg = StubConfig()
        field = SecureField(name="asdf")
        cfg._keyfile.decrypt.side_effect = EncryptionError()
        cfg._keyfile.__exit__.return_value = False

        with pytest.raises(ValueError):
            field.to_python(cfg, {"method": "test", "ciphertext": 10})

    def test_to_python_dict_valid(self):
        cfg = StubConfig()
        field = SecureField(name="asdf")

        assert (
            field.to_python(cfg, {"method": "test", "ciphertext": "aGVsbG8="})
            == "plaintext"
        )

    def test_to_python_invalid_type(self):
        field = SecureField()
        with pytest.raises(ValueError):
            field.to_python(StubConfig(), 100)
