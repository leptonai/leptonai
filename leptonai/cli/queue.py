"""
Queue is a module that provides a way to manage queues on a workspace.
"""

import click
import re

from rich.table import Table

from .util import (
    console,
    click_group,
)
from ..api.v1.client import APIClient


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
    client = APIClient()
    client.queue.create(name=name)
    console.print(
        f"Successfully created queue [green]{name}[/].\nNote that queue creation is"
        " asynchronous, and may take a few seconds. Use [bold]lepton queue list[/]"
        " to check the status of the queue."
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
    client = APIClient()
    queue_list = client.queue.list_all()

    if pattern:
        filtered_queues = [
            queue.name for queue in queue_list if re.match(pattern, queue.name)
        ]
    else:
        filtered_queues = [queue.name for queue in queue_list]
    table = Table(title="Queues", show_lines=True)
    table.add_column("name")
    table.add_column("length")
    for name in filtered_queues:
        # get length
        try:
            queue_length = client.queue.length(name).length
        except Exception:
            queue_length = "[unknown length]"
        table.add_row(name, str(queue_length))

    console.print(table)


@queue.command()
@click.option("--name", "-n", help="Queue name", type=str, required=True)
def remove(name):
    """
    Removes the queue with the given name.
    """
    client = APIClient()
    client.queue.delete(name)
    console.print(
        f"Successfully deleted queue [green]{name}[/].\nNote that queue deletion is"
        " asynchronous, and may take a few seconds. Use [bold]lepton queue list[/]"
        " to check the status of the queue."
    )


@queue.command()
@click.option("--name", "-n", help="Queue name", type=str, required=True)
@click.option("--message", "-m", help="Message to send", type=str, required=True)
def send(name, message):
    """
    Sends a message to the queue with the given name.
    """
    client = APIClient()
    client.queue.send(name, message)
    console.print(f"Successfully sent message to queue [green]{name}[/].")


@queue.command()
@click.option("--name", "-n", help="Queue name", type=str, required=True)
def receive(name):
    """
    Receives a message from the queue with the given name.
    """

    client = APIClient()
    queue_message_list = client.queue.receive(name)

    if queue_message_list is not None and len(queue_message_list) == 0:
        console.print(f"Queue [yellow]{name}[/] is empty.")
        return

    console.print(f"Successfully received message from queue [green]{name}[/]:")
    for queue_message in queue_message_list:
        console.print(queue_message.message)


def add_command(cli_group):
    cli_group.add_command(queue)
