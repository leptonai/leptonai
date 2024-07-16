from .connection import Connection
from .util import json_or_error


def list_nodegroups(conn: Connection):
    """
    List all node groups on a workspace.
    """
    response = conn.get("/dedicated-node-groups")
    return json_or_error(response)
