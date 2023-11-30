"""
KV is a module that provides a way to manage kvs on a workspace.
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
from leptonai.api import kv as api


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
    conn = get_connection_or_die()
    response = api.create_kv(conn, name)
    explain_response(
        response,
        f"Successfully created KV [green]{name}[/].\nNote that KV creation is"
        " asynchronous, and may take a few seconds. Use [bold]lepton kv list[/] to"
        " check the status of the KV.",
        "Failed to create KV [red]{name}[/].",
        "Failed to create KV [red]{name}[/].",
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
    conn = get_connection_or_die()
    response = api.list_kv(conn)
    explain_response(
        response,
        None,
        "Failed to list KVs.",
        "Failed to list KVs.",
        exit_if_4xx=True,
    )
    kvs = response.json()
    if pattern:
        filtered_kvs = [kv["name"] for kv in kvs if re.match(pattern, kv["name"])]
    else:
        filtered_kvs = [kv["name"] for kv in kvs]
    table = Table(title="KVs", show_lines=True)
    table.add_column("name")
    for name in filtered_kvs:
        table.add_row(name)
    console.print(table)


@kv.command()
@click.option("--name", "-n", help="KV name", type=str, required=True)
def remove(name):
    """
    Removes the KV with the given name.
    """
    conn = get_connection_or_die()
    response = api.delete_kv(conn, name)
    explain_response(
        response,
        f"Successfully deleted KV [green]{name}[/].\nNote that KV deletion is"
        " asynchronous, and may take a few seconds. Use [bold]lepton KV list[/] to"
        " check the status of the KV.",
        f"KV [red]{name}[/] does not exist.",
        f"Failed to delete KV [red]{name}[/].",
    )


@kv.command()
@click.option("--name", "-n", help="KV name", type=str, required=True)
@click.option("--key", "-k", help="Key to put", type=str, required=True)
@click.option("--value", "-v", help="Value to put", type=str, required=True)
def putkey(name, key, value):
    """
    Sends a message to the kv with the given name.
    """
    conn = get_connection_or_die()
    response = api.put_key(conn, name, key, value)
    explain_response(
        response,
        f"Successfully put {key} to KV [green]{name}[/].",
        f"KV [red]{name}[/] does not exist.",
        f"Failed to put key {key} to KV [red]{name}[/].",
    )


@kv.command()
@click.option("--name", "-n", help="KV name", type=str, required=True)
@click.option("--key", "-k", help="Key to get", type=str, required=True)
def getkey(name, key):
    """
    Receives a message from the kv with the given name.
    """
    conn = get_connection_or_die()
    response = api.get_key(conn, name, key)
    explain_response(
        response,
        f"Successfully received message from kv [green]{name}[/]:\n{response.text}",
        f"KV [red]{name}[/] or key [red]{key}[/] does not exist.",
        f"Failed to get key {key} from [red]{name}[/].",
    )


@kv.command()
@click.option("--name", "-n", help="KV name", type=str, required=True)
@click.option("--key", "-k", help="Key to delete", type=str, required=True)
def deletekey(name, key):
    """
    Receives a message from the kv with the given name.
    """
    conn = get_connection_or_die()
    response = api.delete_key(conn, name, key)
    explain_response(
        response,
        f"Successfully deleted key {key} from kv [green]{name}[/].",
        f"KV [red]{name}[/] or key [red]{key}[/] does not exist.",
        f"Failed to delete key {key} from [red]{name}[/].",
    )


def add_command(cli_group):
    cli_group.add_command(kv)
