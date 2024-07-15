"""
KV is a module that provides a way to manage kvs on a workspace.
"""
import sys

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


@objectstore.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
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
@click.pass_context
def get(ctx, key, file, public, return_url):
    """
    Gets the object with the given key.
    """
    # backward warning.
    if "--bucket" in ctx.args or "-b" in ctx.args:
        console.print(
            "The '--bucket public' and '--bucket private' options for the 'lep photon objectstore get' command are "
            "deprecated. Please use the '--public' option to get public objects. By default, will get private objects."
        )
        sys.exit(1)
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


@objectstore.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
@click.option("--key", "-k", help="Object key", type=str, required=True)
@click.option("--public", is_flag=True, default=False, help="Is public bucket")
@click.pass_context
def cat(ctx, key, public):
    """
    Gets the object with the given key and prints it to stdout.
    """
    if "--bucket" in ctx.args or "-b" in ctx.args:
        console.print(
            "The '--bucket public' and '--bucket private' options for the 'lep photon objectstore cat' command are "
            "deprecated. Please use the '--public' option to cat public objects. By default, will cat private objects."
        )
        sys.exit(1)

    client = APIClient()

    response = client.object_storage.get(key, public, stream=True)
    for chunk in response.iter_content(chunk_size=4096):
        if chunk:
            print(chunk.decode(), end="")


@objectstore.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
@click.option(
    "--key",
    "-k",
    help="Object key. If not specified, use the filename (including the path).",
    type=str,
)
@click.option("--file", "-f", help="File to upload", type=str, required=True)
@click.option("--public", is_flag=True, default=False, help="Is public bucket")
@click.pass_context
def put(ctx, key, file, public):
    """
    Puts the object with the given key.
    """
    if "--bucket" in ctx.args or "-b" in ctx.args:
        console.print(
            "The '--bucket public' and '--bucket private' options for the 'lep photon objectstore put' command are "
            "deprecated. Please use the '--public' option to put public objects. By default, private objects "
            "will be put."
        )
        sys.exit(1)
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


@objectstore.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
)
)
@click.option("--key", "-k", help="Object key", type=str, required=True)
@click.option("--public", is_flag=True, default=False, help="Is public bucket")
@click.pass_context
def delete(ctx, key, public):
    """
    Deletes the object with the given key.
    """
    if "--bucket" in ctx.args or "-b" in ctx.args:
        console.print(
            "The '--bucket public' and '--bucket private' options for the 'lep photon objectstore delete' command are "
            "deprecated. Please use the '--public' option to delete public objects. By default, private objects "
            "will be deleted."
        )
        sys.exit(1)
    client = APIClient()
    client.object_storage.delete(key, public)
    console.print(f"Successfully deleted object [green]{key}[/].")


@objectstore.command(name="list",
                     context_settings=dict(
                         ignore_unknown_options=True,
                         allow_extra_args=True,
                     )
                     )
@click.option("--prefix", "-p", help="Prefix to filter objects", type=str, default=None)
@click.option("--public", is_flag=True, default=False, help="Is public bucket")
@click.pass_context
def list_command(ctx, prefix, public):
    """
    Lists all objects in the current workspace.
    """
    if "--bucket" in ctx.args or "-b" in ctx.args:
        console.print(
            "The '--bucket public' and '--bucket private' options for the 'lep photon objectstore list' command are "
            "deprecated. Please use the '--public' option to list public objects. By default, private objects "
            "will be listed."
        )
        sys.exit(1)
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
