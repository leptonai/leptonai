"""
Utility functions to help with the tools api commonly used in LLMs.
"""

import inspect
import json
from typing import Callable, Optional, Dict, List, Any, get_type_hints, get_origin

_type_map = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
}


def _get_type_spec(param_type, description):
    """
    Gets the type spec in json format for a specific parameter type.

    The param type must be one of the following: str, int, float, bool, list, or typing.List.
    The description depends on the parameter:
    - For list types, it should be a list of tuples, where each tuple is of length 3, and the first element is a string as the name, the second element is the type of the field, and the third element is the description of the field.
    - For string types, it should either be a string as the description, or a tuple of length 2, where the first element is the string description, and the second element is a list of strings representing the enum.
    - For all other types, it should be a string as the description.
    """
    if get_origin(param_type) in (list, List):
        param_type = list
    try:
        type_name = _type_map[param_type]
    except KeyError:
        raise TypeError(f"Type {param_type} is not supported by the api.")
    if param_type == list:
        if not isinstance(description, list):
            raise TypeError(
                f"For list type {param_type}(aka {type_name}), value must be a list"
                " containing the description of the field."
            )
        array_description = {"type": "object", "properties": {}}
        for i, v in enumerate(description):
            if len(v) != 3 or not isinstance(v[0], str) or not isinstance(v[1], type):
                raise TypeError(
                    "For array type, each element of the list must be a tuple of length"
                    " 3, where the first element is a string, the second element is the"
                    " type of the field, and the third element is the description of"
                    f" the field. Got {v} (index {i})"
                )
            try:
                type_spec = _get_type_spec(v[1], v[2])
            except Exception as e:
                raise TypeError(
                    f"Error when processing the {i}th element of the list {v}. Source"
                    f" exception: {e}"
                )
            array_description["properties"][v[0]] = type_spec
        return {"type": "array", "items": array_description}
    elif param_type == str:
        if isinstance(description, str):
            # simple string type
            return {"type": type_name, "description": description}
        elif (
            len(description) == 2
            and type(description[0]) == str
            and type(description[1]) == list
        ):
            # string type with enum
            if not all(isinstance(v, str) for v in description[1]):
                raise TypeError(
                    f"For string type {param_type}(aka {type_name}) with an enum, the"
                    " enum must be a list of strings."
                )
            return {
                "type": type_name,
                "description": description[0],
                "enum": description[1],
            }
        else:
            raise TypeError(
                f"For string type, value must be a"
                f" string containing the description of the field, or a tuple of length"
                f" 2 where the first element is the description of the field and the"
                f" second element is a list of strings representing the enum."
            )
    else:
        if not isinstance(description, str):
            raise TypeError(
                f"For type {param_type}, value must be a"
                " string containing the description of the field."
            )
        return {"type": type_name, "description": description}


def get_tools_spec(func: Callable, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Given a function stub, return a dictionary that is OpenAI tools api compatible
    for function calling. Note that since the OpenAI tools api is not explicitly
    documented, this is a best effort implementation.

    Args:
        func: a function, or a simple stub, which defines its parameters and properly
            annotates the types of the parameters, using default values to provide
            the description of the parameters.
        name: (optional) the name of the function. If not provided, the name of the
            function will be used.
    Returns:
        A dictionary that is OpenAI tools api compatible for function calling.
    """
    if not callable(func):
        raise TypeError("func must be a callable object.")
    function_name = name if name else func.__name__
    docstring = inspect.getdoc(func)
    # get the annotations of the function parameters
    type_hints = get_type_hints(func)
    # get the default values of the function parameters
    signature = inspect.signature(func)
    parameters = signature.parameters

    # Constructing the JSON structure
    function_info = {
        "name": function_name,
        "description": docstring,
        "parameters": {"type": "object", "properties": {}},
    }

    # Adding parameter information to the JSON structure
    for param_name, param in parameters.items():
        # Determine the type of the parameter
        try:
            param_type = type_hints[param_name]
        except KeyError:
            raise TypeError(f"Parameter {param_name} does not have a type annotation.")
        # Determine the default value/description of the parameter
        if param.default is inspect.Parameter.empty:
            raise TypeError(
                f"Parameter {param_name} does not have a description specified as its"
                " default value."
            )
        default_value = param.default
        # Add parameter information to the JSON structure
        function_info["parameters"]["properties"][param_name] = _get_type_spec(
            param_type, default_value
        )

    return function_info
