import json
from typing import List, Any

try:
    # For Python 3.9 and later
    from typing import Annotated  # type: ignore
except ImportError:
    # For Python versions below 3.9
    from typing_extensions import Annotated  # type: ignore
import unittest

from leptonai.util import tool


def my_test_function_stub(
    str_param: str = "this is a str description",
    string_enum_param: str = (
        "this is a string enum description",
        ["value1", "value2"],
    ),  # type: ignore
    int_param: int = "this is an int description",  # type: ignore
    float_param: float = "this is a float description",  # type: ignore
    bool_param: bool = "this is a bool description",  # type: ignore
    list_param: List[Any] = [
        ("param1", str, "this is a list str element description"),
        ("param2", int, "this is a list int element description"),
    ],
):
    """
    my documentation string.
    """
    pass


def my_test_function_stub_annotated(
    str_param: Annotated[str, "this is a str description"],
    string_enum_param: Annotated[
        str,
        (
            "this is a string enum description",
            ["value1", "value2"],
        ),
    ],
    int_param: Annotated[int, "this is an int description"],
    float_param: Annotated[float, "this is a float description"],
    bool_param: Annotated[bool, "this is a bool description"],
    list_param: Annotated[
        List[Any],
        [
            ("param1", str, "this is a list str element description"),
            ("param2", int, "this is a list int element description"),
        ],
    ],
):
    """
    my documentation string.
    """
    pass


def my_test_function_stub_annotated2(
    str_param: Annotated[str, "this is a str description"],
    string_enum_param: Annotated[
        str,
        (
            "this is a string enum description",
            ["value1", "value2"],
        ),
    ],
    int_param: Annotated[int, "this is an int description"],
    float_param: Annotated[float, "this is a float description"],
    bool_param: Annotated[bool, "this is a bool description"],
    list_param: Annotated[
        List[Any],
        [
            ("param1", Annotated[str, "this is a list str element description"]),
            ("param2", Annotated[int, "this is a list int element description"]),
        ],
    ],
):
    """
    my documentation string.
    """
    pass


ground_truth = """{
  "name": "my_test_function_stub",
  "description": "my documentation string.",
  "parameters": {
    "type": "object",
    "properties": {
      "str_param": {
        "type": "string",
        "description": "this is a str description"
      },
      "string_enum_param": {
        "type": "string",
        "description": "this is a string enum description",
        "enum": [
          "value1",
          "value2"
        ]
      },
      "int_param": {
        "type": "integer",
        "description": "this is an int description"
      },
      "float_param": {
        "type": "number",
        "description": "this is a float description"
      },
      "bool_param": {
        "type": "boolean",
        "description": "this is a bool description"
      },
      "list_param": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "param1": {
              "type": "string",
              "description": "this is a list str element description"
            },
            "param2": {
              "type": "integer",
              "description": "this is a list int element description"
            }
          }
        }
      }
    }
  }
}
"""


def get_n_day_weather_forecast(
    location: str = "The city and state, e.g. San Francisco, CA",
    format: str = (
        "The temperature unit to use. Infer this from the users location.",
        ["celsius", "fahrenheit"],
    ),  # type: ignore
    num_days: int = "The number of days to forecast",  # type: ignore
):
    """
    Get an N-day weather forecast
    """
    pass


def get_n_day_weather_forecast_annotated(
    location: Annotated[str, "The city and state, e.g. San Francisco, CA"],
    format: Annotated[
        str,
        (
            "The temperature unit to use. Infer this from the users location.",
            ["celsius", "fahrenheit"],
        ),
    ],
    num_days: Annotated[int, "The number of days to forecast"],
):
    """
    Get an N-day weather forecast
    """
    pass


weather_ground_truth = """{
    "name": "get_n_day_weather_forecast",
    "description": "Get an N-day weather forecast",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA"
            },
            "format": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "The temperature unit to use. Infer this from the users location."
            },
            "num_days": {
                "type": "integer",
                "description": "The number of days to forecast"
            }
        }
    }
}
"""


class TestTool(unittest.TestCase):
    def test_get_spec(self):
        self.assertEqual(
            tool.get_tools_spec(my_test_function_stub), json.loads(ground_truth)
        )
        self.assertEqual(
            tool.get_tools_spec(
                my_test_function_stub_annotated, name="my_test_function_stub"
            ),
            json.loads(ground_truth),
        )
        self.assertEqual(
            tool.get_tools_spec(
                my_test_function_stub_annotated2, name="my_test_function_stub"
            ),
            json.loads(ground_truth),
        )

    def test_n_day_weather_forecast(self):
        self.assertEqual(
            tool.get_tools_spec(get_n_day_weather_forecast),
            json.loads(weather_ground_truth),
            json.dumps(tool.get_tools_spec(get_n_day_weather_forecast), indent=4),
        )

    def test_n_day_weather_forecast_annotated(self):
        spec = tool.get_tools_spec(
            get_n_day_weather_forecast_annotated, name="get_n_day_weather_forecast"
        )
        self.assertEqual(
            spec,
            json.loads(weather_ground_truth),
            json.dumps(spec, indent=4),
        )


if __name__ == "__main__":
    unittest.main()
