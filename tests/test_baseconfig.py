from unittest.mock import patch, MagicMock
import pytest
from cincoconfig.abc import BaseConfig, BaseSchema, Field
from cincoconfig.encryption import KeyFile


class TestBaseConfig:

    def test_add_field_dynamic(self):
        schema = BaseSchema(dynamic=True)
        config = BaseConfig(schema)
        assert config._add_field('hello', 'world') == 'world'
        assert config._fields['hello'] == 'world'

    def test_add_field_failed(self):
        schema = BaseSchema()
        config = BaseConfig(schema)

        with pytest.raises(TypeError):
            config._add_field('hello', 'world')

    def test_get_field_base(self):
        schema = BaseSchema()
        schema._fields['hello'] = 'world'
        config = BaseConfig(schema)

        assert config._get_field('hello') == 'world'

    def test_get_field_dynamic(self):
        schema = BaseSchema()
        config = BaseConfig(schema)
        config._fields['hello'] = 'world'
        assert config._get_field('hello') == 'world'

    def test_key_filename_ctor(self):
        cfg = BaseConfig(BaseSchema(), key_filename='asdf.txt')
        assert cfg._key_filename == 'asdf.txt'
        assert cfg._BaseConfig__keyfile.filename == 'asdf.txt'

    def test_key_filename_none_ctor(self):
        cfg = BaseConfig(BaseSchema())
        assert cfg._key_filename is BaseConfig.DEFAULT_CINCOKEY_FILEPATH

    def test_key_filename_parent(self):
        parent = BaseConfig(BaseSchema(), key_filename='asdf.txt')
        child = BaseConfig(BaseSchema(), parent)
        assert child._key_filename == 'asdf.txt'

    def test_key_filename_setter(self):
        parent = BaseConfig(BaseSchema(), key_filename='asdf.txt')
        child = BaseConfig(BaseSchema(), parent)
        child._key_filename = 'qwer.txt'
        assert child._key_filename == 'qwer.txt'
        assert parent._key_filename == 'asdf.txt'

    def test_key_filename_set_none(self):
        parent = BaseConfig(BaseSchema(), key_filename='asdf.txt')
        child = BaseConfig(BaseSchema(), parent, key_filename='qwer.txt')
        child._key_filename = None
        assert child._key_filename == 'asdf.txt'
        assert parent._key_filename == 'asdf.txt'

    def test_keyfile_set(self):
        parent = BaseConfig(BaseSchema(), key_filename='asdf.txt')
        child = BaseConfig(BaseSchema(), parent, key_filename='qwer.txt')
        assert child._keyfile is not parent._keyfile

    def test_keyfile_parent(self):
        parent = BaseConfig(BaseSchema(), key_filename='asdf.txt')
        child = BaseConfig(BaseSchema(), parent)
        assert child._keyfile is parent._keyfile

    @patch('cincoconfig.abc.BaseConfig.DEFAULT_CINCOKEY_FILEPATH', '/path/to/cincokey')
    def test_keyfile_default(self):
        parent = BaseConfig(BaseSchema())
        child = BaseConfig(BaseSchema(), parent)
        assert child._keyfile is parent._keyfile
        assert child._keyfile.filename == '/path/to/cincokey'

    def test_full_path(self):
        parent = BaseConfig(BaseSchema(key='root'))
        child = BaseConfig(BaseSchema(key='child'), parent=parent)
        assert child._full_path() == 'root.child'

    def test_full_path_container(self):
        parent = BaseConfig(BaseSchema(key='root'))
        child = BaseConfig(BaseSchema(key='child'), parent=parent)
        child._container = MagicMock()
        child._container._get_item_position = MagicMock()
        child._container._get_item_position.return_value = '1'
        assert child._full_path() == 'root.child[1]'
        child._container._get_item_position.assert_called_once_with(child)
