import pytest
from cincoconfig.formats.ini import IniConfigFormat


class TestIniConfigFormat:

    def test_init(self):
        with pytest.raises(NotImplementedError):
            x = IniConfigFormat()

    def test_loads(self):
        with pytest.raises(NotImplementedError):
            IniConfigFormat.loads(None, None, b'x = 1')

    def test_dumps(self):
        with pytest.raises(NotImplementedError):
            IniConfigFormat.dumps(None, None, {'x': 1})
