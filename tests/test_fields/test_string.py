#
# Copyright (C) 2021 Adam Meily
#
# This file is subject to the terms and conditions defined in the file 'LICENSE', which is part of
# this source code package.
#

import pytest

from cincoconfig.fields import (
    StringField,
    LogLevelField,
    ApplicationModeField,
    VirtualField,
    UrlField,
)


class MockConfig:
    def __init__(self):
        self._data = {}

    def __getitem__(self, key):
        return self._data[key]


class MockSchema:
    def __init__(self):
        self._fields = {}
        self._env_prefix = False

    def _add_field(self, name, field):
        self._fields[name] = field
        field.__setkey__(self, name)


class TestStringField:
    def setup_method(self, method=None):
        self.cfg = MockConfig()

    def test_invalid_case(self):
        with pytest.raises(TypeError):
            field = StringField(transform_case="ASDF")

    def test_case_lower(self):
        field = StringField(transform_case="lower")
        assert field.validate(self.cfg, "HELLO") == "hello"

    def test_case_upper(self):
        field = StringField(transform_case="upper")
        assert field.validate(self.cfg, "hello") == "HELLO"

    def test_case_preserve(self):
        field = StringField()
        assert field.validate(self.cfg, "HellO") == "HellO"

    def test_min_length_valid(self):
        field = StringField(min_len=5)
        assert field.validate(self.cfg, "hello") == "hello"

    def test_min_length_invalid(self):
        field = StringField(min_len=6)
        with pytest.raises(ValueError):
            field.validate(self.cfg, "hello")

    def test_max_length_valid(self):
        field = StringField(max_len=5)
        assert field.validate(self.cfg, "hello") == "hello"

    def test_max_length_invalid(self):
        field = StringField(max_len=4)
        with pytest.raises(ValueError):
            field.validate(self.cfg, "hello")

    def test_regex_match(self):
        field = StringField(regex="^h.*$")
        assert field.validate(self.cfg, "hello") == "hello"

    def test_regex_no_match(self):
        field = StringField(regex="^H.*$")
        with pytest.raises(ValueError):
            field.validate(self.cfg, "hello")

    def test_strip_preserve(self):
        field = StringField()
        assert field.validate(self.cfg, " hello ") == " hello "

    def test_strip_whitespace(self):
        field = StringField(transform_strip=True)
        assert field.validate(self.cfg, "  hello  ") == "hello"

    def test_strip_custom(self):
        field = StringField(transform_strip="/")
        assert field.validate(self.cfg, "// hello  ///") == " hello  "

    def test_choice_valid(self):
        field = StringField(choices=["a", "b", "c"])
        assert field.validate(self.cfg, "a") == "a"

    def test_choice_invalid(self):
        field = StringField(choices=["a", "b", "c"])
        with pytest.raises(ValueError):
            field.validate(self.cfg, "z")

    def test_choice_lower_valid(self):
        field = StringField(choices=["a", "b", "c"], transform_case="lower")
        assert field.validate(self.cfg, "A") == "a"

    def test_choice_error_message_list(self):
        field = StringField(choices=["a", "b", "c"])
        with pytest.raises(ValueError) as excinfo:
            field.validate(self.cfg, "qwer")

        assert str(excinfo.value).endswith(" a, b, c")

    def test_choice_error_message_too_many(self):
        field = StringField(choices=["a", "b", "c", "d", "e", "f", "g"])
        with pytest.raises(ValueError) as excinfo:
            field.validate(self.cfg, "qwer")

        assert not str(excinfo.value).endswith(" a, b, c, d, e, f, g")

    def test_non_string(self):
        field = StringField()
        with pytest.raises(ValueError):
            field.validate(self.cfg, 100)

    def test_empty_string_requied(self):
        field = StringField(required=True)
        with pytest.raises(ValueError):
            field.validate(self.cfg, "")

    def test_empty_string_not_required(self):
        field = StringField(required=False)
        assert field.validate(self.cfg, "") == ""


class TestLogLevelField:
    def test_default_levels(self):
        field = LogLevelField()
        assert field.levels == ["debug", "info", "warning", "error", "critical"]
        assert field.levels == field.choices
        assert field.transform_case == "lower"
        assert field.transform_strip is True

    def test_custom_levels(self):
        field = LogLevelField(levels=["hello", "goodbye"])
        assert field.levels == ["hello", "goodbye"]
        assert field.levels == field.choices

    def test_custom_case(self):
        field = LogLevelField(transform_case="upper")
        assert field.transform_case == "upper"

    def test_custom_strip(self):
        field = LogLevelField(transform_strip="/")
        assert field.transform_strip == "/"


class TestApplicationModeField:
    def setup_method(self, method=None):
        self.ms = MockSchema()
        self.cfg = MockConfig()

    def test_default_levels(self):
        field = ApplicationModeField()
        assert field.modes == ["development", "production"]
        assert field.choices == field.modes
        assert field.transform_case == "lower"
        assert field.transform_strip is True

    def test_create_helpers(self):
        field = ApplicationModeField(modes=["production"])
        self.ms._add_field("mode", field)
        assert isinstance(self.ms._fields["is_production_mode"], VirtualField)
        assert self.ms._fields["is_production_mode"]._key == "is_production_mode"

    def test_call_helpers(self):
        field = ApplicationModeField(default="production")
        self.cfg._data["mode"] = "production"
        self.ms._add_field("mode", field)
        assert self.ms._fields["is_production_mode"].__getval__(self.cfg) is True
        assert self.ms._fields["is_development_mode"].__getval__(self.cfg) is False

    def test_no_helpers(self):
        field = ApplicationModeField(modes=["production"], create_helpers=False)
        self.ms._add_field("mode", field)
        assert "is_production_mode" not in self.ms._fields

    @pytest.mark.parametrize("value", ["he llo", "hel-lo", "$hello", ">hello"])
    def test_invalid_mode_name(self, value):
        with pytest.raises(TypeError):
            field = ApplicationModeField(modes=[value])


class TestUrlField:
    def test_valid_url(self):
        field = UrlField()
        url = "http://google.com:8086/api"
        assert field.validate(MockConfig(), url) == url

    def test_invalid_url(self):
        field = UrlField()
        with pytest.raises(ValueError):
            field.validate(MockConfig(), "not a url")
