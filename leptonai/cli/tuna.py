import click

from rich.table import Table

from .util import (
    console,
    click_group,
)
from ..api.v1.client import APIClient


@click_group()
def tuna():
    """
    todo
    description here

    data,
        upload
        list

    train
        create
        list
        stop

    model
        list
        delete
        run

    """
    pass


@tuna.command()
def upload(local_path, remote_path):
    upload(
        local_path,
        remote_path,
        resync=True,
    )
    pass


@tuna.command()
def train():
    pass


@tuna.command()
def list():
    pass


@tuna.command()
def run():
    pass


@tuna.command()
def delete():
    pass


@tuna.command(name="list")
def list_command():
    """
    Lists all secrets in the current workspace. Note that the secret values are
    always hidden.
    """
    client = APIClient()
    secrets = client.secret.list_all()
    secrets.sort()
    table = Table(title="Secrets", show_lines=True)
    table.add_column("ID")
    table.add_column("Value")
    for secret in secrets:
        table.add_row(secret, "(hidden)")
    console.print(table)


@tuna.command()
@click.option("--name", "-n", help="Secret name")
def remove(name):
    """
    Removes the secret with the given name.
    """
    client = APIClient()
    client.secret.delete(name)
    console.print(f"Secret [green]{name}[/] deleted successfully.")


def add_command(cli_group):
    cli_group.add_command(tuna)
