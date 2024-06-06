"""
KV is a module that provides a way to manage kvs on a workspace.
"""

import click
import re

from rich.table import Table

from leptonai.api.v1.client import APIClient
from .util import console, click_group


@click_group()
def kv():
    """
    Manage KV stores on the Lepton AI cloud.

    The Lepton Key-Value store. Every named KV can be considered the equivalent
    of a conventional KV / table / collection, composed of keys as strings and
    values as bytes.

    The kv commands allow you to create, list, and remove KVs on the
    Lepton AI cloud.
    """
    pass


@kv.command()
@click.option("--name", "-n", help="KV name", type=str, required=True)
def create(name):
    """
    Creates a KV of the given name.
    """
    c = APIClient()
    c.kv.create_namespace(name)
    console.print(
        f"Successfully created KV [green]{name}[/].\nNote that KV creation is"
        " asynchronous, and may take a few seconds. Use [bold]lepton kv list[/] to"
        " check the status of the KV."
    )


@kv.command(name="list")
@click.option(
    "--pattern", help="Regular expression pattern to filter KV names", default=None
)
def list_command(pattern):
    """
    Lists all kvs in the current workspace. Note that the kv values are
    always hidden.
    """
    c = APIClient()
    kvs = c.kv.list_namespaces()
    if pattern:
        kvs = [kv for kv in kvs if re.match(pattern, kv.metadata.name)]  # type: ignore
    table = Table(title="KV", show_lines=True)
    table.add_column("name")
    for kv in kvs:
        table.add_row(kv.metadata.name)
    console.print(table)


@kv.command()
@click.option("--name", "-n", help="KV name", type=str, required=True)
def remove(name):
    """
    Removes the KV with the given name.
    """
    c = APIClient()
    c.kv.delete_namespace(name)
    console.print(
        f"Successfully deleted KV [green]{name}[/].\nNote that KV deletion is"
        " asynchronous, and may take a few seconds. Use [bold]lepton KV list[/] to"
        " check the status of the KV."
    )


@kv.command()
@click.option("--name", "-n", help="KV name", type=str, required=True)
@click.option("--key", "-k", help="Key to put", type=str, required=True)
@click.option("--value", "-v", help="Value to put", type=str, required=True)
def putkey(name, key, value):
    """
    Sends a message to the kv with the given name.
    """
    c = APIClient()
    c.kv.put(name, key, value)
    console.print(f"Successfully put key [green]{key}[/] to KV [green]{name}[/].")


@kv.command()
@click.option("--name", "-n", help="KV name", type=str, required=True)
@click.option("--key", "-k", help="Key to get", type=str, required=True)
def getkey(name, key):
    """
    Receives a message from the kv with the given name.
    """
    c = APIClient()
    value = c.kv.get(name, key)
    console.print(
        f"Successfully received message from kv [green]{name}[/] and key"
        f" [green]{key}[/]:\n{value}",
    )


@kv.command()
@click.option("--name", "-n", help="KV name", type=str, required=True)
@click.option("--key", "-k", help="Key to delete", type=str, required=True)
def deletekey(name, key):
    """
    Receives a message from the kv with the given name.
    """
    c = APIClient()
    c.kv.delete(name, key)
    console.print(
        f"Successfully deleted key {key} from kv [green]{name}[/].",
    )


def add_command(cli_group):
    cli_group.add_command(kv)
