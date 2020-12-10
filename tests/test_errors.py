from cincoconfig.abc import ValidationError


class TestValidationError:

    def test_set_friendly_name(self):
        err = ValidationError(None, None, None)
        err.friendly_name = 'asdf'
        assert err.friendly_name == 'asdf'
        assert err._friendly_name == 'asdf'
