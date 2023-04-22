import yaml as yaml_lib
from unittest.mock import patch
import pytest
from cincoconfig.formats import yaml


class TestYamlConfigFormat:
    def test_available(self):
        assert yaml.IS_AVAILABLE
        yaml.YamlConfigFormat()

    @patch("cincoconfig.formats.yaml.IS_AVAILABLE", False)
    def test_not_available(self):
        with pytest.raises(TypeError):
            x = yaml.YamlConfigFormat()

    def test_dumps(self):
        fmt = yaml.YamlConfigFormat()
        obj = {"x": 1}
        assert (
            fmt.dumps(None, obj) == yaml_lib.dump(obj, Dumper=yaml_lib.Dumper).encode()
        )

    def test_loads(self):
        fmt = yaml.YamlConfigFormat()
        obj = {"x": 1}
        bobj = yaml_lib.dump(obj, Dumper=yaml_lib.Dumper).encode()
        assert fmt.loads(None, bobj) == obj

    def test_dumps_root_key(self):
        fmt = yaml.YamlConfigFormat(root_key="CONFIG")
        obj = {"x": 1}
        assert (
            fmt.dumps(None, obj)
            == yaml_lib.dump({"CONFIG": obj}, Dumper=yaml_lib.Dumper).encode()
        )

    def test_loads_root_key(self):
        fmt = yaml.YamlConfigFormat(root_key="CONFIG")
        obj = {"x": 1}
        root_obj = {"CONFIG": obj}
        bobj = yaml_lib.dump(root_obj, Dumper=yaml_lib.Dumper).encode()
        assert fmt.loads(None, bobj) == obj
