#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import os
from unittest.mock import patch, PropertyMock
import pytest
from cincoconfig.fields import FilenameField


class MockConfig:
    def __init__(self, data=None):
        self._data = data or {}


class TestFilenameField:
    def test_resolve_relative(self):
        field = FilenameField(startdir=os.getcwd())
        assert field.validate(MockConfig(), "file.txt") == os.path.join(
            os.getcwd(), "file.txt"
        )

    def test_absolute(self):
        field = FilenameField(startdir=os.getcwd())
        assert (
            field.validate(MockConfig(), os.path.sep + "file.txt")
            == os.path.sep + "file.txt"
        )

    @patch("os.path.sep", "\\")
    def test_convert_win_slashes(self):
        field = FilenameField()
        assert field.validate(MockConfig(), "/file.txt") == "\\file.txt"

    @patch("os.path.exists")
    def test_exists_true_true(self, exists):
        exists.return_value = True
        field = FilenameField(exists=True)
        assert field.validate(MockConfig(), "file.txt") == "file.txt"
        exists.assert_called_once_with("file.txt")

    @patch("os.path.exists")
    def test_exists_true_false(self, exists):
        exists.return_value = False
        field = FilenameField(exists=True)
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "file.txt")

        exists.assert_called_once_with("file.txt")

    @patch("os.path.exists")
    def test_exists_false_true(self, exists):
        exists.return_value = True
        field = FilenameField(exists=False)
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "file.txt")
        exists.assert_called_once_with("file.txt")

    @patch("os.path.exists")
    def test_exists_false_false(self, exists):
        exists.return_value = False
        field = FilenameField(exists=False)
        assert field.validate(MockConfig(), "file.txt") == "file.txt"
        exists.assert_called_once_with("file.txt")

    @patch("os.path.isdir")
    def test_dir_true(self, isdir):
        isdir.return_value = True
        field = FilenameField(exists="dir")
        assert field.validate(MockConfig(), "some-dir") == "some-dir"
        isdir.assert_called_once_with("some-dir")

    @patch("os.path.isdir")
    def test_dir_false(self, isdir):
        isdir.return_value = False
        field = FilenameField(exists="dir")
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "some-dir")
        isdir.assert_called_once_with("some-dir")

    @patch("os.path.isfile")
    def test_file_true(self, isfile):
        isfile.return_value = True
        field = FilenameField(exists="file")
        assert field.validate(MockConfig(), "some-file") == "some-file"
        isfile.assert_called_once_with("some-file")

    @patch("os.path.isfile")
    def test_file_false(self, isfile):
        isfile.return_value = False
        field = FilenameField(exists="file")
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "some-file")
        isfile.assert_called_once_with("some-file")

    def test_empty_not_required(self):
        field = FilenameField(exists=True)
        assert field.validate(MockConfig(), "") == ""

    def test_empty_required(self):
        field = FilenameField(required=True, exists=True)
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "")
