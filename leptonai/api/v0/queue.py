# Because most of the apis in queue do not return json, we will not use json_or_error here.
from .connection import Connection


def list_queue(conn: Connection):
    """
    List queues in the current workspace.
    """
    response = conn.get("/queue")
    return response


def create_queue(conn: Connection, name: str):
    """
    Create a queue in the current workspace.
    """
    response = conn.post("/queue", json={"name": name})
    return response


def delete_queue(conn: Connection, name: str):
    """
    Delete a queue from the current workspace.
    """
    response = conn.delete(f"/queue/{name}")
    return response


def length(conn: Connection, name: str):
    """
    Get the length of a queue.
    """
    response = conn.get(f"/queue/{name}/length")
    return response


def receive(conn: Connection, name: str):
    """
    Receives a message from a queue.
    """
    response = conn.get(f"/queue/{name}/messages")
    return response


def send(conn: Connection, name: str, message: str):
    """
    Put a message in the queue.
    """
    response = conn.post(f"/queue/{name}/messages", json={"message": message})
    return response
