"""
KV is a module that provides a way to manage kvs on a workspace.
"""

import click
import os

from rich.table import Table

from .util import (
    console,
    click_group,
    get_connection_or_die,
    explain_response,
    sizeof_fmt,
)
from leptonai.api import objectstore as api


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
@click.option("--bucket", "-b", help="Bucket name", type=str, default="private")
@click.option(
    "--return-url",
    "-u",
    help=(
        "Return the url of the object instead of the content. If specified, --file"
        " takes no effect."
    ),
    is_flag=True,
)
def get(key, file, bucket, return_url):
    """
    Gets the object with the given key.
    """
    if not file:
        file = os.path.basename(key)
    conn = get_connection_or_die()
    response = api.get(conn, key, bucket, return_url=return_url, stream=True)
    explain_response(
        response,
        None,
        f"Object [red]{key}[/] not found.",
        f"Failed to download object [red]{key}[/].",
        exit_if_4xx=True,
    )
    if return_url:
        console.print(response.headers.get("Location"))
    else:
        console.print(f"Downloading object [green]{key}[/] to [green]{file}[/].")
        with open(file, "wb") as file:
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    file.write(chunk)


@objectstore.command()
@click.option("--key", "-k", help="Object key", type=str, required=True)
@click.option("--bucket", "-b", help="Bucket name", type=str, default="private")
def cat(key, bucket):
    """
    Gets the object with the given key and prints it to stdout.
    """
    conn = get_connection_or_die()
    response = api.get(conn, key, bucket, stream=True)
    explain_response(
        response,
        None,
        f"Object [red]{key}[/] not found.",
        f"Failed to download object [red]{key}[/].",
    )
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
@click.option("--bucket", "-b", help="Bucket name", type=str, default="private")
def put(key, file, bucket):
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
    conn = get_connection_or_die()
    if not os.path.exists(file):
        console.print(f"File [red]{file}[/] does not exist.")
        return
    with open(file, "rb") as f:
        response = api.put(conn, key, f, bucket)
        explain_response(
            response,
            f"Successfully uploaded object [green]{key}[/].",
            f"Failed to upload object [red]{key}[/].",
            f"Failed to upload object [red]{key}[/].",
        )


@objectstore.command()
@click.option("--key", "-k", help="Object key", type=str, required=True)
@click.option("--bucket", "-b", help="Bucket name", type=str, default="private")
def delete(key, bucket):
    """
    Deletes the object with the given key.
    """
    conn = get_connection_or_die()
    response = api.delete(conn, key, bucket)
    explain_response(
        response,
        f"Successfully deleted object [green]{key}[/].",
        f"Object [red]{key}[/] does not exist.",
        f"Failed to delete object [red]{key}[/].",
    )


@objectstore.command(name="list")
@click.option("--bucket", "-b", help="Bucket name", type=str, default="private")
@click.option("--prefix", "-p", help="Prefix to filter objects", type=str, default=None)
def list_command(bucket, prefix):
    """
    Lists all objects in the current workspace.
    """
    conn = get_connection_or_die()
    response = api.list_objects(conn, bucket, prefix)
    explain_response(
        response,
        "List of objects in the current workspace:",
        "Failed to list objects.",
        "Failed to list objects.",
    )
    items = response.json().get("items", [])
    if not items:
        console.print("No objects found.")
    else:
        items.sort(key=lambda x: x["key"])
        table = Table(title="Objects", show_lines=True)
        table.add_column("key")
        table.add_column("size")
        for item in items:
            table.add_row(item["key"], sizeof_fmt(item["size"]))
        console.print(table)


def add_command(cli_group):
    cli_group.add_command(objectstore)
