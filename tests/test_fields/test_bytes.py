#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import base64
import pytest
from cincoconfig.fields import BytesField


class MockConfig:
    def __init__(self):
        self._parent = None
        self._key = None

    def _full_path(self):
        return ""


class TestBytesField:
    def test_init_valid_encoding(self):
        field = BytesField("hex")
        assert field.encoding == "hex"

    def test_init_invalid_encoding(self):
        with pytest.raises(TypeError):
            BytesField("asdf")

    def test_validate_str(self):
        field = BytesField()
        field._validate(MockConfig(), "hello") == b"hello"

    def test_validate_bytes(self):
        field = BytesField()
        assert field._validate(None, b"hello") == b"hello"

    def test_validate_invalid_type(self):
        field = BytesField(name="asdf")
        with pytest.raises(ValueError):
            field._validate(MockConfig(), 100)

    def test_to_basic_none(self):
        field = BytesField(name="asdf")
        field.to_basic(MockConfig(), None) is None

    def test_to_basic_base64(self):
        field = BytesField("base64")
        assert (
            field.to_basic(MockConfig(), b"hello")
            == base64.b64encode(b"hello").decode()
        )

    def test_to_basic_hex(self):
        field = BytesField("hex")
        assert field.to_basic(MockConfig(), b"hello") == b"hello".hex()

    def test_to_basic_invalid(self):
        field = BytesField(name="asdf")
        field.encoding = "adsf"
        with pytest.raises(TypeError):
            field.to_basic(MockConfig(), "asdf")

    def test_to_python_none(self):
        field = BytesField()
        assert field.to_python(MockConfig(), None) is None

    def test_to_python_not_str(self):
        field = BytesField(name="asdf")
        with pytest.raises(ValueError):
            field.to_python(MockConfig(), 100)

    def test_to_python_base64_valid(self):
        field = BytesField("base64")
        assert (
            field.to_python(MockConfig(), base64.b64encode(b"hello").decode())
            == b"hello"
        )

    def test_to_python_base64_invalid(self):
        field = BytesField("base64")
        with pytest.raises(ValueError):
            field.to_python(MockConfig(), "hello")

    def test_to_python_hex_valid(self):
        field = BytesField("hex")
        assert field.to_python(MockConfig(), "deadbeef") == b"\xde\xad\xbe\xef"

    def test_to_python_hex_invalid(self):
        field = BytesField("hex")
        with pytest.raises(ValueError):
            field.to_python(MockConfig(), "hello")

    def test_to_python_invalid(self):
        field = BytesField(name="asdf")
        field.encoding = "adsf"
        with pytest.raises(TypeError):
            field.to_python(MockConfig(), "asdf")
