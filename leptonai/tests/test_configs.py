from pydantic import BaseModel
from typing import Dict
import unittest


class TestPydanticCompatib(unittest.TestCase):
    def test_compatible_root_model(self):
        from leptonai.config import CompatibleRootModel

        class TestModel(CompatibleRootModel[Dict[str, str]]):
            root: Dict[str, str] = {}

        test_model = TestModel()
        self.assertEqual(test_model.root, {})
        self.assertEqual(test_model.dict(), {})
        self.assertEqual(test_model.json(), "{}")
        test_model.root = {"key": "value"}
        self.assertEqual(test_model.root, {"key": "value"})
        self.assertEqual(test_model.dict(), {"key": "value"})
        self.assertEqual(test_model.json(), '{"key":"value"}')

    def test_compatible_field_validator(self):
        from leptonai.config import compatible_field_validator

        class TestModel(BaseModel):
            field: str

            @compatible_field_validator("field")
            def field_cannot_be_moo(cls, value):
                if value == "moo":
                    raise ValueError("Field cannot be moo")
                return value

        test_model = TestModel(field="bar")
        self.assertEqual(test_model.field, "bar")
        with self.assertRaises(ValueError):
            test_model = TestModel(field="moo")

    def test_v2only_field_validator(self):
        from leptonai.config import v2only_field_validator, PYDANTIC_MAJOR_VERSION

        class TestModel(BaseModel):
            field: str

            @v2only_field_validator("field")
            def field_cannot_be_moo(cls, value):
                if value == "moo":
                    raise ValueError("Field cannot be moo")
                return value

        test_model = TestModel(field="bar")
        self.assertEqual(test_model.field, "bar")
        if PYDANTIC_MAJOR_VERSION > 1:
            with self.assertRaises(ValueError):
                test_model = TestModel(field="moo")
        else:
            # v2only validators will not be called in pydantic v1
            test_model = TestModel(field="moo")
            self.assertEqual(test_model.field, "moo")


if __name__ == "__main__":
    unittest.main()
