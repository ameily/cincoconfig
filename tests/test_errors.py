from cincoconfig.core import ValidationError, Schema, Field


class TestValidationError:
    def test_set_ref_path(self):
        err = ValidationError(None, None, None, ref_path="asdf")
        assert err.ref_path == "asdf"
        assert err._ref_path == "asdf"

    def test_ref_path(self):
        schema = Schema()
        field = schema.x = Field()
        config = schema()
        err = ValidationError(config, field, None)
        assert err.ref_path == "x"
