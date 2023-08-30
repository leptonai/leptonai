from typing import List

from .connection import Connection
from .util import json_or_error


def create_secret(conn: Connection, names: List[str], values: List[str]):
    """
    Create a secret with the given name and value.

    :param str name: name of the secret
    :param str value: the value of the secret

    :return: the response from the server
    """
    request_body = [
        {"name": name, "value": value} for name, value in zip(names, values)
    ]
    response = conn.post("/secrets", json=request_body)
    return response


def list_secret(conn: Connection):
    """
    List all secrets on a workspace.
    """
    response = conn.get("/secrets")
    return json_or_error(response)


def remove_secret(conn: Connection, name: str):
    """
    Remove a secret from a workspace.
    """
    response = conn.delete("/secrets/" + name)
    return response
