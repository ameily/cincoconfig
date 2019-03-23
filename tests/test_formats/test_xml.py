import pytest
from cincoconfig.formats.xml import XmlConfigFormat


class TestXmlConfigFormat:

    def test_init(self):
        with pytest.raises(NotImplementedError):
            x = XmlConfigFormat()

    def test_loads(self):
        with pytest.raises(NotImplementedError):
            XmlConfigFormat.loads(None, None, b'<x>1</x>')

    def test_dumps(self):
        with pytest.raises(NotImplementedError):
            XmlConfigFormat.dumps(None, None, {'x': 1})
