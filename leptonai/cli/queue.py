"""
Queue is a module that provides a way to manage queues on a workspace.
"""

import click
import re

from rich.table import Table

from .util import (
    console,
    click_group,
    get_connection_or_die,
    explain_response,
)
from leptonai.api import queue as api


@click_group()
def queue():
    """
    Manage queues on the Lepton AI cloud.

    Lepton provides a simple to use message queue for sending messages between
    deployments. For example, you can use the queue functionality to build a
    distributed task manager.

    The queue commands allow you to create, list, and remove queues on the
    Lepton AI cloud.
    """
    pass


@queue.command()
@click.option("--name", "-n", help="Queue name", type=str, required=True)
def create(name):
    """
    Creates a queue of the given name.
    """
    conn = get_connection_or_die()
    response = api.create_queue(conn, name)
    explain_response(
        response,
        f"Successfully created queue [green]{name}[/].\nNote that queue creation is"
        " asynchronous, and may take a few seconds. Use [bold]lepton queue list[/] to"
        " check the status of the queue.",
        "Failed to create queue [red]{name}[/].",
        "Failed to create queue [red]{name}[/].",
    )


@queue.command(name="list")
@click.option(
    "--pattern", help="Regular expression pattern to filter queue names", default=None
)
def list_command(pattern):
    """
    Lists all queues in the current workspace. Note that the queue values are
    always hidden.
    """
    conn = get_connection_or_die()
    response = api.list_queue(conn)
    explain_response(
        response,
        None,
        "Failed to list queues.",
        "Failed to list queues.",
        exit_if_4xx=True,
    )
    queues = response.json()
    if pattern:
        filtered_queues = [
            queue["name"] for queue in queues if re.match(pattern, queue["name"])
        ]
    else:
        filtered_queues = [queue["name"] for queue in queues]
    table = Table(title="Queues", show_lines=True)
    table.add_column("name")
    table.add_column("length")
    for name in filtered_queues:
        # get length
        response = api.length(conn, name)
        if response.ok:
            length = response.json()["length"]
            table.add_row(name, str(length))
        else:
            table.add_row(name, "[unknown length]")

    console.print(table)


@queue.command()
@click.option("--name", "-n", help="Queue name", type=str, required=True)
def remove(name):
    """
    Removes the queue with the given name.
    """
    conn = get_connection_or_die()
    response = api.delete_queue(conn, name)
    explain_response(
        response,
        f"Successfully deleted queue [green]{name}[/].\nNote that queue deletion is"
        " asynchronous, and may take a few seconds. Use [bold]lepton queue list[/] to"
        " check the status of the queue.",
        f"Queue [red]{name}[/] does not exist.",
        f"Failed to delete queue [red]{name}[/].",
    )


@queue.command()
@click.option("--name", "-n", help="Queue name", type=str, required=True)
@click.option("--message", "-m", help="Message to send", type=str, required=True)
def send(name, message):
    """
    Sends a message to the queue with the given name.
    """
    conn = get_connection_or_die()
    response = api.send(conn, name, message)
    explain_response(
        response,
        f"Successfully sent message to queue [green]{name}[/].",
        f"Queue [red]{name}[/] does not exist.",
        f"Failed to send message to queue [red]{name}[/].",
    )


@queue.command()
@click.option("--name", "-n", help="Queue name", type=str, required=True)
def receive(name):
    """
    Receives a message from the queue with the given name.
    """
    conn = get_connection_or_die()
    response = api.receive(conn, name)
    if response.ok and len(response.json()) == 0:
        console.print(f"Queue [yellow]{name}[/] is empty.")
        return
    else:
        explain_response(
            response,
            f"Successfully received message from queue [green]{name}[/]:",
            f"Queue [red]{name}[/] does not exist.",
            f"Failed to receive message from queue [red]{name}[/].",
        )
        console.print(response.json()[0]["message"])


def add_command(cli_group):
    cli_group.add_command(queue)
