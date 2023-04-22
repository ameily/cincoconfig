import pickle
from cincoconfig.formats.pickle import PickleConfigFormat


class TestPickleConfigFormat:
    def test_dumps(self):
        fmt = PickleConfigFormat()
        obj = {"x": 1}
        assert fmt.dumps(None, obj) == pickle.dumps(obj)

    def test_loads(self):
        fmt = PickleConfigFormat()
        obj = {"x": 1}
        pobj = pickle.dumps(obj)
        assert fmt.loads(None, pobj) == obj
