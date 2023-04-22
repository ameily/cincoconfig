from unittest.mock import patch
import pytest
import bson as bson_lib
from cincoconfig.formats import bson


class TestBsonConfigFormat:
    def test_available(self):
        assert bson.IS_AVAILABLE
        bson.BsonConfigFormat()

    @patch("cincoconfig.formats.bson.IS_AVAILABLE", False)
    def test_not_available(self):
        with pytest.raises(TypeError):
            x = bson.BsonConfigFormat()

    def test_dumps(self):
        fmt = bson.BsonConfigFormat()
        obj = {"x": 1}
        assert fmt.dumps(None, obj) == bson_lib.dumps(obj)

    def test_loads(self):
        fmt = bson.BsonConfigFormat()
        obj = {"x": 1}
        bobj = bson_lib.dumps(obj)
        assert fmt.loads(None, bobj) == obj
