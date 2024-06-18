from importlib import reload
import os
from pydantic import BaseModel
from typing import Dict
import unittest

try:
    import torch

    torch_available = True
except ImportError:
    torch_available = False


class TestConfig(unittest.TestCase):
    @unittest.skipIf(not torch_available, "Pytorch is not available")
    def test_is_rocm_flag(self):
        from leptonai import config

        # Since we cannot really control the underlying hardware, we try our best
        # to test the flag.
        if torch.cuda.is_available():
            self.assertEqual(config._is_rocm(), (torch.version.hip is not None))
        os.environ["LEPTON_BASE_IMAGE_FORCE_ROCM"] = "true"
        reload(config)
        self.assertTrue(config._is_rocm())
        self.assertIn("photon-rocm-py", config.BASE_IMAGE)
        self.assertNotIn("photon-py", config.BASE_IMAGE)

        os.environ["LEPTON_BASE_IMAGE_FORCE_ROCM"] = "false"
        reload(config)
        self.assertFalse(config._is_rocm())
        self.assertNotIn("photon-rocm-py", config.BASE_IMAGE)
        self.assertIn("photon-py", config.BASE_IMAGE)


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
