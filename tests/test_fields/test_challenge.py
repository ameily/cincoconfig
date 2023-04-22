import base64
import hashlib
from unittest.mock import patch, MagicMock

import pytest

from cincoconfig.fields import ChallengeField, DigestValue
from cincoconfig.core import Config, Schema


class MockConfig:
    def __init__(self):
        self._parent = None
        self._key = None

    def _full_path(self):
        return ""


class TestDigestValue:
    def test_str(self):
        salt = base64.b64encode(b"salt")
        digest = base64.b64encode(b"digest")
        val = DigestValue(b"salt", b"digest", hashlib.sha256)
        assert str(val) == "%s:%s" % (salt.decode(), digest.decode())

    def test_parse(self):
        val = DigestValue(b"salt", b"digest", hashlib.sha256)
        val2 = DigestValue.parse(str(val), hashlib.sha256)

        assert val == val2

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            DigestValue.parse("asdf", hashlib.md5)

    def test_challenge_success(self):
        salt = b"salt"
        digest = hashlib.md5(b"saltmessage").digest()
        val = DigestValue(salt, digest, hashlib.md5)
        val.challenge("message")
        val.challenge(b"message")

    def test_challenge_failed(self):
        salt = b"salt"
        digest = hashlib.md5(b"message").digest()
        val = DigestValue(salt, digest, hashlib.md5)
        with pytest.raises(ValueError):
            val.challenge(b"m3ssage")

    def test_create_no_salt(self):
        msg = "message"
        val = DigestValue.create(msg, hashlib.md5)
        assert len(val.salt) == hashlib.md5().digest_size

    def test_create_trunc_salt(self):
        msg = "message"
        digest_size = hashlib.sha1().digest_size
        salt = b"x" * (digest_size + 10)
        val = DigestValue.create(msg, hashlib.sha1, salt=salt)
        assert len(val.salt) == digest_size
        assert val.salt == (b"x" * digest_size)

    def test_create_short_salt(self):
        msg = b"message"
        digest_size = hashlib.sha256().digest_size
        salt = b"x" * (digest_size - 1)
        with pytest.raises(TypeError):
            DigestValue.create(msg, hashlib.sha256, salt=salt)

    def test_create_salt_exact(self):
        msg = "message"
        digest_size = hashlib.sha256().digest_size
        salt = b"x" * digest_size
        val = DigestValue.create(msg, hashlib.sha256, salt=salt)
        assert val.salt == salt


class TestChallengeField:
    def test_valid_default(self):
        val = ChallengeField("md5", default=DigestValue.create("digest", hashlib.md5))

    def test_invalid_algorithm(self):
        with pytest.raises(TypeError):
            ChallengeField("asdf")

    def test_validate_str(self):
        field = ChallengeField("md5")
        val = field._validate(MockConfig(), b"digest")
        assert val.digest == hashlib.md5(val.salt + b"digest").digest()

    def test_validate_tuple(self):
        val = DigestValue(b"salt", b"digest", hashlib.md5)
        field = ChallengeField("md5")
        assert field._validate(MockConfig(), val) is val

    def test_validate_error(self):
        field = ChallengeField("md5", name="asdf")
        with pytest.raises(ValueError):
            field._validate(MockConfig(), 100)

    @patch.object(DigestValue, "create")
    def test_hash(self, create_mock):
        field = ChallengeField("md5")
        field._hash("message", b"salt")
        create_mock.assert_called_with("message", hashlib.md5, salt=b"salt")

    def test_to_basic(self):
        field = ChallengeField("md5")
        assert field.to_basic(
            MockConfig(), DigestValue(b"salt", b"digest", hashlib.md5)
        ) == {
            "salt": base64.b64encode(b"salt").decode(),
            "digest": base64.b64encode(b"digest").decode(),
        }

    def test_to_basic_none(self):
        field = ChallengeField("md5")
        assert field.to_basic(MockConfig(), None) is None

    def test_to_python_dict(self):
        field = ChallengeField("md5")
        salt = base64.b64encode(b"salt").decode()
        digest = base64.b64encode(b"digest").decode()
        val = field.to_python(MockConfig(), {"salt": salt, "digest": digest})
        assert val.salt == b"salt"
        assert val.digest == b"digest"
        assert val.algorithm is hashlib.md5

    def test_to_python_str(self):
        field = ChallengeField("md5")
        field._hash = MagicMock()
        field.to_python(MockConfig(), "message")
        field._hash.assert_called_with("message")

    def test_to_python_error(self):
        field = ChallengeField("md5")
        with pytest.raises(ValueError):
            field.to_python(MockConfig(), 100)

    def test_to_python_invalid_salt(self):
        field = ChallengeField("md5")
        with pytest.raises(ValueError):
            field.to_python(
                MockConfig(),
                {"salt": "==Zaa", "digest": base64.b64encode(b"digest").decode()},
            )

    def test_to_python_invalid_digest(self):
        field = ChallengeField("md5")
        with pytest.raises(ValueError):
            field.to_python(
                MockConfig(),
                {"salt": base64.b64encode(b"salt").decode(), "digest": "==Za"},
            )

    @patch.object(DigestValue, "create")
    def test_set_default_str(self, create_mock):
        create_mock.return_value = "hello"
        field = ChallengeField("md5", default="default", key="test")
        cfg = Config(Schema())
        field.__setdefault__(cfg)
        create_mock.assert_called_with("default", hashlib.md5)
        assert cfg._data["test"] == "hello"

    def test_set_default_tuple(self):
        sdt = DigestValue.create("hello", hashlib.md5)
        field = ChallengeField("md5", key="test", default=sdt)
        cfg = Config(Schema())
        field.__setdefault__(cfg)
        assert cfg._data["test"] is sdt

    def test_set_default_error(self):
        field = ChallengeField("md5", default=100)
        with pytest.raises(TypeError):
            field.__setdefault__({})

    def test_set_default_none(self):
        cfg = Config(Schema())
        field = ChallengeField("md5", key="test")
        field.__setdefault__(cfg)
        assert cfg._data["test"] is None

    def test_to_python_none(self):
        field = ChallengeField("md5", key="test")
        assert field.to_python(MockConfig(), None) is None
