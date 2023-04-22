from unittest.mock import patch, mock_open, MagicMock
import pytest
from cincoconfig.encryption import (
    KeyFile,
    AesProvider,
    EncryptionError,
    XorProvider,
    SecureValue,
)


class StubProvider:
    def __init__(self):
        self.encrypt = MagicMock(return_value=b"ciphertext")
        self.decrypt = MagicMock(return_value=b"plaintext")


class TestKeyFile:
    @patch.object(KeyFile, "_KeyFile__load_key")
    def test_with(self, load_key):
        kf = KeyFile("asdf.txt")
        with kf as kf2:
            kf._KeyFile__key = "asdf"
            assert kf is kf2
            assert kf._KeyFile__refcount == 1
            load_key.assert_called_once_with()

            with kf as kf3:
                assert kf._KeyFile__refcount == 2
                assert kf3 is kf
                assert kf._KeyFile__key == "asdf"

            assert kf._KeyFile__refcount == 1
            assert kf._KeyFile__key == "asdf"

        assert kf._KeyFile__refcount == 0
        assert kf._KeyFile__key is None

    @patch("cincoconfig.encryption.open", new_callable=mock_open, read_data=b"x" * 32)
    @patch.object(KeyFile, "_validate_key")
    @patch.object(KeyFile, "generate_key")
    def test_load_key_exists(self, genkey_mock, validate_mock, open_mock):
        kf = KeyFile("asdf.txt")
        kf._KeyFile__load_key()

        assert kf._KeyFile__key == b"x" * 32
        open_mock.assert_called_once_with("asdf.txt", "rb")
        validate_mock.assert_called_once_with()
        genkey_mock.assert_not_called()

    @patch("cincoconfig.encryption.open")
    @patch.object(KeyFile, "_KeyFile__generate_key")
    def test_load_generate(self, genkey_mock, open_mock):
        open_mock.side_effect = IOError()
        kf = KeyFile("asdf.txt")
        kf._KeyFile__load_key()

        open_mock.assert_called_once_with("asdf.txt", "rb")
        genkey_mock.assert_called_once_with()

    @patch("cincoconfig.encryption.open", new_callable=mock_open)
    @patch("os.urandom")
    def test_generate_key(self, urandom_mock, open_mock):
        urandom_mock.return_value = b"x" * 32
        kf = KeyFile("asdf.txt")
        kf.generate_key()

        open_mock.assert_called_once_with("asdf.txt", "wb")
        handle = open_mock()
        handle.write.assert_called_once_with(b"x" * 32)
        urandom_mock.assert_called_once_with(32)

    def test_validate_none(self):
        kf = KeyFile("asdf")
        with pytest.raises(EncryptionError):
            kf._validate_key()

    def test_validate_short(self):
        kf = KeyFile("asdf")
        kf._KeyFile__key = b"x" * 31
        with pytest.raises(EncryptionError):
            kf._validate_key()

    def test_validate_success(self):
        kf = KeyFile("asdf")
        kf._KeyFile__key = b"x" * 32
        kf._validate_key()

    def test_get_provider_aes(self):
        kf = KeyFile("asdf.txt")
        kf._KeyFile__key = b"x" * 32
        provider, method = kf._get_provider("aes")
        assert isinstance(provider, AesProvider)
        assert provider._AesProvider__key == b"x" * 32
        assert method == "aes"

    def test_get_provider_xor(self):
        kf = KeyFile("asdf.txt")
        kf._KeyFile__key = b"x" * 32
        provider, method = kf._get_provider("xor")
        assert isinstance(provider, XorProvider)
        assert provider._XorProvider__key == b"x" * 32
        assert method == "xor"

    def test_get_provider_unknown(self):
        kf = KeyFile("asdf.txt")
        kf._KeyFile__key = b"x" * 32
        with pytest.raises(TypeError):
            kf._get_provider("balh")

    def test_get_provider_no_key(self):
        kf = KeyFile("asdf.txt")
        with pytest.raises(TypeError):
            kf._get_provider("xor")

    def test_encrypt(self):
        provider = StubProvider()
        kf = KeyFile("asdf.txt")
        kf._KeyFile__key = b"x" * 32
        kf._get_provider = MagicMock(return_value=(provider, "test"))

        secret = kf.encrypt("hello", "test")
        provider.encrypt.assert_called_once_with(b"hello")
        kf._get_provider.assert_called_once_with("test")
        assert secret == SecureValue("test", b"ciphertext")

    def test_decrypt(self):
        provider = StubProvider()
        kf = KeyFile("asdf.txt")
        kf._KeyFile__key = b"x" * 32
        kf._get_provider = MagicMock(return_value=(provider, "test"))

        text = kf.decrypt(SecureValue("test", b"hello"))
        provider.decrypt.assert_called_once_with(b"hello")
        kf._get_provider.assert_called_once_with("test")
        assert text == b"plaintext"

    def test_encrypt_nokey(self):
        kf = KeyFile("asdf.txt")
        with pytest.raises(TypeError):
            kf.encrypt(b"hello")

    def test_decrypt_nokey(self):
        kf = KeyFile("asdf.txt")
        with pytest.raises(TypeError):
            kf.decrypt(b"asdf")

    def test_encrypt_best_aes(self):
        kf = KeyFile("asdf.txt")
        kf._KeyFile__key = b"x" * 32
        provider, method = kf._get_provider(method="best")
        assert isinstance(provider, AesProvider)
        assert method == "aes"

    @patch("cincoconfig.encryption.AES_AVAILABLE", False)
    def test_encrypt_best_xor(self):
        kf = KeyFile("asdf.txt")
        kf._KeyFile__key = b"x" * 32
        provider, method = kf._get_provider(method="best")
        assert isinstance(provider, XorProvider)
        assert method == "xor"


class TestAesProvider:
    def test_encrypt_decrypt(self):
        provider = AesProvider(b"x" * 32)
        secret = provider.encrypt(b"hello world")
        plaintext = provider.decrypt(secret)

        assert len(secret) == 32
        assert plaintext == b"hello world"
        assert secret != plaintext

    @patch("cincoconfig.encryption.AES_AVAILABLE", False)
    def test_aes_unavailable(self):
        with pytest.raises(TypeError):
            AesProvider(b"x" * 32)

    def test_decrypt_bad_value(self):
        provider = AesProvider(b"x" * 32)
        with pytest.raises(EncryptionError):
            provider.decrypt(b"x" * 31)


class TestXorProvider:
    def test_encrypt_decrypt(self):
        provider = XorProvider(b"x" * 32)
        secret = provider.encrypt(b"hello world")
        plaintext = provider.decrypt(secret)

        assert len(secret) == len(b"hello world")
        assert secret != plaintext
        assert plaintext == b"hello world"
