import json
from cincoconfig.formats.json import JsonConfigFormat


class TestJsonConfigFormat:
    def test_dumps(self):
        fmt = JsonConfigFormat(pretty=False)
        obj = {"x": 1}
        assert fmt.dumps(None, obj) == json.dumps(obj).encode()

    def test_loads(self):
        fmt = JsonConfigFormat()
        obj = {"x": 1}
        jobj = json.dumps(obj).encode()
        assert fmt.loads(None, jobj) == obj

    def test_dumps_pretty(self):
        fmt = JsonConfigFormat(pretty=True)
        obj = {"x": 1}
        assert fmt.dumps(None, obj) == json.dumps(obj, indent=2).encode()
