from unittest.mock import MagicMock
from cincoconfig.core import ConfigType, ConfigTypeField


class TestConfigTypeField:

    def test_setdefault(self):
        mock_ct = MagicMock()
        retval = mock_ct.return_value = object()
        cfg = MagicMock()
        cfg._data = {}
        field = ConfigTypeField(mock_ct, key='x')
        field.__setdefault__(cfg)
        assert cfg._data == {'x': retval}
        mock_ct.assert_called_once_with(cfg)

    def test_call(self):
        mock_ct = MagicMock()
        retval = mock_ct.return_value = object()
        cfg = MagicMock()
        field = ConfigTypeField(mock_ct, key='x')
        assert field(cfg) is retval
        mock_ct.assert_called_once_with(cfg)
