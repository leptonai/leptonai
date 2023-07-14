"""
Pickled is a simple utility that allows one to pickle an object and return it to
the client side. This is useful especially when in debug or experimentation phase,
where you want to return a complex object to the client side for further inspection,
and you control both the server side and the client side.

Please do note that, such convenience comes with caveats:

(1) You need to make sure that the client side has the same class definition as
the server side. Otherwise, you will get an error when unpickling the object.
(2) Similar to the standard pickle, you should not unpickle an object from an
untrusted source. This is because unpickling an object can execute arbitrary
code, which can be dangerous.

If you want to return a complex object to the client side, and you do not control
both the server and client side at the same time, consider using industry standard
serialization formats such as json, protobuf, msgpack, thrift, etc. (in no particular
order).
"""

import base64
import pickle
from typing import Any, Dict

_PICKLED_PREFIX = "lepton_pickled"


def is_pickled(obj: Dict[str, str]) -> bool:
    """
    Checks if a string is a pickled string.

    Args:
        content (str): The string to check.

    Returns:
        bool: True if the string is a pickled string, False otherwise.
    """
    try:
        return obj["type"] == _PICKLED_PREFIX
    except Exception:
        return False


def lepton_pickle(obj: Any) -> str:
    """
    Pickles an object and returns an objec that will be able to be sent over the
    api.

    Args:
        obj (Any): The object to pickle.

    Returns:
        content: a dictionary with two keys: "type" and "content". "type" has value
            "lepton_pickled", and "content" is the pickled string. However, do not
            rely on this format as it may change in the future.
    """
    return {
        "type": _PICKLED_PREFIX,
        "content": base64.b64encode(pickle.dumps(obj)).decode("utf-8"),
    }


def lepton_unpickle(content: str) -> Any:
    """
    Unpickles a string to an object.

    Args:
        content (str): The pickled string.

    Returns:
        Any: The unpickled object.
    """
    content = content["content"]
    try:
        return pickle.loads(base64.b64decode(content))
    except Exception as e:
        raise ValueError(f"Cannot unpickle content. Detailed error message: {str(e)}")
