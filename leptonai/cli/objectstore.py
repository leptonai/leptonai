"""
KV is a module that provides a way to manage kvs on a workspace.
"""

import click
from datetime import datetime
import os

from rich.table import Table

from .util import (
    console,
    click_group,
    sizeof_fmt,
)
from ..api.v1.client import APIClient

_max_upload_file_size_limit = 4995 * 1024 * 1024


@click_group()
def objectstore():
    """
    Manage the object store on the Lepton AI cloud. (beta)
    """
    pass


@objectstore.command()
@click.option("--key", "-k", help="Object key", type=str, required=True)
@click.option("--file", "-f", help="File to write to.", type=str, default=None)
@click.option("--public", "-p", is_flag=True, default=False, help="Is public bucket")
@click.option(
    "--return-url",
    "-u",
    help=(
        "Return the url of the object instead of the content. If specified, --file"
        " takes no effect."
    ),
    is_flag=True,
)
def get(key, file, public, return_url):
    """
    Gets the object with the given key.
    """
    if not file:
        file = os.path.basename(key)
    client = APIClient()

    response = client.object_storage.get(
        key, return_url=return_url, is_public=public, stream=True
    )
    if return_url:
        console.print(response.headers.get("Location"))
    else:
        console.print(f"Downloading object [green]{key}[/] to [green]{file}[/].")
        with open(file, "wb") as file_writer:
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    file_writer.write(chunk)
    console.print(
        f"Successfully downloaded object [green]{key}[/] to [green]{file}[/]."
    )


@objectstore.command()
@click.option("--key", "-k", help="Object key", type=str, required=True)
@click.option("--public", is_flag=True, default=False, help="Is public bucket")
def cat(key, public):
    """
    Gets the object with the given key and prints it to stdout.
    """
    client = APIClient()

    response = client.object_storage.get(key, public, stream=True)
    for chunk in response.iter_content(chunk_size=4096):
        if chunk:
            print(chunk.decode(), end="")


@objectstore.command()
@click.option(
    "--key",
    "-k",
    help="Object key. If not specified, use the filename (including the path).",
    type=str,
)
@click.option("--file", "-f", help="File to upload", type=str, required=True)
@click.option("--public", is_flag=True, default=False, help="Is public bucket")
def put(key, file, public):
    """
    Puts the object with the given key.
    """
    if not key:
        key = file
    if os.path.getsize(file) > _max_upload_file_size_limit:
        console.print(
            f"File [red]{file}[/] exceeds the size limit allowed by the objectstore."
        )
        return

    client = APIClient()
    if not os.path.exists(file):
        console.print(f"File [red]{file}[/] does not exist.")
        return
    with open(file, "rb") as f:
        client.object_storage.put(key, f, public)
        console.print(f"Successfully uploaded object [green]{key}[/].")


@objectstore.command()
@click.option("--key", "-k", help="Object key", type=str, required=True)
@click.option("--public", is_flag=True, default=False, help="Is public bucket")
def delete(key, public):
    """
    Deletes the object with the given key.
    """

    client = APIClient()
    client.object_storage.delete(key, public)
    console.print(f"Successfully deleted object [green]{key}[/].")


@objectstore.command(name="list")
@click.option("--prefix", "-p", help="Prefix to filter objects", type=str, default=None)
@click.option("--public", is_flag=True, default=False, help="Is public bucket")
def list_command(prefix, public):
    """
    Lists all objects in the current workspace.
    """

    client = APIClient()

    storage_metadatas = client.object_storage.list(prefix, public)
    console.print("List of objects in the current workspace:")

    items = storage_metadatas.items

    if not items:
        console.print("No objects found.")
    else:
        items.sort(key=lambda x: x.key)
        table = Table(title="Objects", show_lines=True)
        table.add_column("key")
        table.add_column("size")
        table.add_column("last modified")
        for item in items:
            try:
                date = datetime.fromtimestamp(item.last_modified / 1000).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except KeyError:
                date = "N/A"
            table.add_row(item.key, sizeof_fmt(item.size), date)
        console.print(table)


def add_command(cli_group):
    cli_group.add_command(objectstore)
