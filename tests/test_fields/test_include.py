from unittest.mock import MagicMock, mock_open, patch
from cincoconfig.fields import IncludeField


class MockConfigFormat:
    def __init__(self):
        self.retval = {"x": 1, "y": 2, "z": {"a": 3}}
        self.loads = MagicMock(return_value=self.retval)


class MockConfig:
    def __init__(self, data=None):
        self._data = data or {}


class TestIncludeField:
    def test_combine_trees(self):
        base = {"a": 1, "b": {"x": 2}, "c": 3}
        child = {"c": 5, "b": {"y": 4}, "d": 6}
        field = IncludeField()

        field.combine_trees(base, child) == {
            "a": 1,
            "b": {"x": 2, "y": 4},
            "c": 5,
            "d": 6,
        }

    @patch(
        "cincoconfig.fields.include_field.open",
        new_callable=mock_open,
        read_data=b"hello",
    )
    def test_include(self, mop):
        field = IncludeField()
        fmt = MockConfigFormat()
        cfg = MockConfig()
        base = {"b": 2}

        field.combine_trees = MagicMock(return_value={"a": 1})
        field.validate = MagicMock(return_value="blah.txt")
        ret = field.include(cfg, fmt, "blah.txt", base)
        assert ret == {"a": 1}
        mop.assert_called_once_with("blah.txt", "rb")
        mop().read.assert_called_once_with()
        field.validate.assert_called_once_with(cfg, "blah.txt")
        field.combine_trees.assert_called_once_with(base, fmt.retval)
        fmt.loads.assert_called_once_with(cfg, b"hello")

    @patch(
        "cincoconfig.fields.include_field.open", new_callable=mock_open, read_data=b"{}"
    )
    @patch("cincoconfig.core.os.path.expanduser")
    def test_include_expanduser(self, expanduser, mop):
        field = IncludeField()
        fmt = MockConfigFormat()
        cfg = MockConfig()
        expanduser.return_value = "/home/asdf/blah.txt"
        base = {"b": 2}

        field.combine_trees = MagicMock(return_value={"a": 1})
        field.validate = MagicMock(return_value="blah.txt")
        field.include(cfg, fmt, "blah.txt", base)
        mop.assert_called_once_with("/home/asdf/blah.txt", "rb")
        expanduser.assert_called_once_with("blah.txt")
