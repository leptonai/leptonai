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
import zlib

_PICKLED_PREFIX = "lepton_pickled"

# Typing alias for python typing hints
LeptonPickled = Dict[str, Any]


def is_pickled(obj: LeptonPickled) -> bool:
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


def lepton_pickle(obj: Any, compression: int = -1) -> LeptonPickled:
    """
    Pickles an object and returns an objec that will be able to be sent over the
    api.

    Args:
        obj (Any): The object to pickle.
        compression (int): the compression level used in lepton pickle, between
            0 to 9 or -1. 0 means no compression, 1-9 means progrssively more
            compression applied (hence slower). Default=-1 means the default
            zlib compression chosen by zlib to be a balance between speed and
            compression.

    Returns:
        content: a dictionary with two keys: "type" and "content". "type" has value
            "lepton_pickled", and "content" is the pickled string. However, do not
            rely on this format as it may change in the future.
    """
    try:
        content = pickle.dumps(obj)
    except Exception as e:
        raise ValueError(f"Object is unpicklable. Detailed error message: {str(e)}.")
    if compression < -1 or compression > 9:
        raise ValueError(f"Incorrect level of compression: {compression}.")
    content = zlib.compress(content, level=compression)
    pickled = {
        "type": _PICKLED_PREFIX,
        "compression": compression,
        "content": base64.b64encode(content).decode("utf-8"),
    }
    return pickled


def lepton_unpickle(obj: LeptonPickled) -> Any:
    """
    Unpickles a string to an object.

    Args:
        content (str): The pickled string.

    Returns:
        Any: The unpickled object.
    """
    content = base64.b64decode(obj["content"])
    content = zlib.decompress(content)
    try:
        return pickle.loads(content)
    except Exception as e:
        raise ValueError(f"Cannot unpickle content. Detailed error message: {str(e)}")
