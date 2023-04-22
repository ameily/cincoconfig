import pytest
from cincoconfig.formats.xml import XmlConfigFormat

TEST_DOC = b"""
<config>
    <valid_int type="int">1</valid_int>
    <invalid_int type="int">asdf</invalid_int>

    <valid_float type="float">2.5</valid_float>
    <invalid_float type="float">asdf</invalid_float>

    <valid_true type="bool">true</valid_true>
    <valid_false type="bool">false</valid_false>
    <invalid_bool type="bool">asdf</invalid_bool>

    <valid_str type="str">asdf</valid_str>

    <valid_null type="none" />

    <valid_list type="list">
        <item type="int">1</item>
        <item type="int">2</item>
    </valid_list>

    <valid_dict type="dict">
        <sub1 type="str">blah</sub1>
        <sub2 type="str">blah2</sub2>
    </valid_dict>

    <no_type>asdf</no_type>
</config>
"""

TEST_TREE = {
    "valid_int": 1,
    "invalid_int": "asdf",
    "valid_float": 2.5,
    "invalid_float": "asdf",
    "valid_true": True,
    "valid_false": False,
    "invalid_bool": "asdf",
    "valid_str": "asdf",
    "valid_null": None,
    "valid_list": [1, 2],
    "valid_dict": {"sub1": "blah", "sub2": "blah2"},
    "no_type": "asdf",
}


class BadType:
    pass


class TestXmlConfigFormat:
    def test_loads(self):
        fmt = XmlConfigFormat()
        obj = fmt.loads(None, TEST_DOC)

        assert obj == TEST_TREE

    def test_dumps(self):
        fmt = XmlConfigFormat()
        content = fmt.dumps(None, TEST_TREE)
        obj = fmt.loads(None, content)
        assert obj == TEST_TREE

    def test_loads_incorrect_root(self):
        fmt = XmlConfigFormat(root_tag="BLAH")
        with pytest.raises(ValueError):
            fmt.loads(None, TEST_DOC)

    def test_non_basic_type(self):
        fmt = XmlConfigFormat()
        with pytest.raises(TypeError):
            fmt.dumps(None, {"x": BadType()})
