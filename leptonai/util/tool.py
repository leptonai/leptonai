"""
Utility functions to help with the tools api commonly used in LLMs.
"""

import inspect
from typing import Callable, Optional, Dict, List, Any, get_type_hints, get_origin

try:
    # For Python 3.9 and later
    from typing import _AnnotatedAlias  # type: ignore
except ImportError:
    # For Python versions below 3.9
    from typing_extensions import _AnnotatedAlias  # type: ignore

_type_map = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
}


def _original_type_backward_compatibility(param_type):
    """
    This function is for backward compatibility with Python 3.8 and below.
    It returns the original type of the parameter, which is the same as the
    param_type if the Python version is 3.9 and above, but is the __origin__ of
    the param_type if the Python version is 3.8 and below.
    """
    try:
        return param_type.__origin__
    except AttributeError:
        return param_type


def _get_type_spec(param_type, param_annotation, default_value):
    """
    Gets the type spec in json format for a specific parameter type.

    The param type must be one of the following: str, int, float, bool, list, or typing.List. There are two ways to annotate a parameter: one is via Annotated[type, description], and one is via the default value as the description.

    The description depends on the parameter:
    - For list types, it should be a list of tuples, where each tuple is of length 3, and the first element is a string as the name, the second element is the type of the field, and the third element is the description of the field.
    - For string types, it should either be a string as the description, or a tuple of length 2, where the first element is the string description, and the second element is a list of strings representing the enum.
    - For all other types, it should be a string as the description.

    For example, for an int field, you can do
        def foo(int_param: Annotated[int, "this is an int description"])
    or
        def foo(int_param: int = "this is an int description")
    (note that the default value must be a string in this case, which is a bit hacky, but it works.
    It is recommended that you use Annotated whenever possible.)
    """
    if get_origin(param_type) in (list, List):
        param_type = list
    try:
        type_name = _type_map[param_type]
    except KeyError:
        raise TypeError(f"Type {param_type} is not supported by the api.")
    # We will first prefer the annotation, then the default value, to find the
    # description of the parameter.
    if isinstance(param_annotation, _AnnotatedAlias):
        description = param_annotation.__metadata__
        description = (
            description[0]
            if isinstance(description, tuple) and len(description) == 1
            else description
        )
    elif default_value is not inspect.Parameter.empty:
        description = default_value
    else:
        raise ValueError("Either param_annotation or default_value must be provided.")

    if param_type is list:
        if not isinstance(description, list):
            raise TypeError(
                f"For list type {param_type}(aka {type_name}), value must be a list"
                " containing the description of the field."
            )
        array_description = {"type": "object", "properties": {}}
        for i, v in enumerate(description):
            if len(v) == 2:
                sub_param_name = _original_type_backward_compatibility(v[0])
                sub_param_annotation = v[1]
                sub_param_type = v[1].__origin__
                sub_param_default_value = inspect.Parameter.empty
            elif len(v) == 3:
                sub_param_name = _original_type_backward_compatibility(v[0])
                sub_param_annotation = v[1]
                sub_param_type = v[1]
                sub_param_default_value = v[2]
            else:
                raise TypeError(
                    "For array type, each element of the list must be a tuple of"
                    " length 2 or 3, where the first element is a string, the second"
                    " element is the Annotated type (if len==2) or raw type (if"
                    " len==3) of the field, and the third element (if len==3) is the"
                    f" description of the field. Got {v} (index {i})"
                )
            try:
                type_spec = _get_type_spec(
                    sub_param_type, sub_param_annotation, sub_param_default_value
                )
            except Exception as e:
                raise TypeError(
                    f"Error when processing the {i}th element of the list {v}. Source"
                    f" exception: {e}"
                )
            array_description["properties"][sub_param_name] = type_spec
        return {"type": "array", "items": array_description}
    elif param_type is str:
        if isinstance(description, str):
            # simple string type
            return {"type": type_name, "description": description}
        elif (
            len(description) == 2
            and isinstance(description[0], str)
            and isinstance(description[1], list)
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
                "For string type, value must be a string containing the description of"
                " the field, or a tuple of length 2 where the first element is the"
                " description of the field and the second element is a list of strings"
                f" representing the enum. Got {description}."
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
            annotates the types of the parameters, using Annotated[...], or default
            values to provide the description of the parameters.
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
    annotations = func.__annotations__

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
            param_type = _original_type_backward_compatibility(type_hints[param_name])
        except KeyError:
            raise TypeError(f"Parameter {param_name} does not have a type annotation.")
        # Determine the annotation of the parameter
        param_annotation = annotations.get(param_name)
        # Determine the default value/description of the parameter
        default_value = param.default
        # Add parameter information to the JSON structure
        function_info["parameters"]["properties"][param_name] = _get_type_spec(
            param_type, param_annotation, default_value
        )

    return function_info
