from cincoconfig.core import ValidationError


class TestValidationError:

    def test_set_ref_path(self):
        err = ValidationError(None, None, None, ref_path='asdf')
        assert err.ref_path == 'asdf'
        assert err._ref_path == 'asdf'
