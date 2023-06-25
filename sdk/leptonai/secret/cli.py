import click
import sys

from rich.console import Console
from rich.table import Table

import leptonai.remote as remote
from . import api


console = Console(highlight=False)


@click.group()
def secret():
    pass


@secret.command()
@click.option("--name", "-n", help="Secret name", multiple=True)
@click.option("--value", "-v", help="Secret value", multiple=True)
def create(name, value):
    if len(name) == 0:
        console.print("No secret name given.")
        sys.exit(1)
    if len(name) != len(value):
        console.print("Number of names and values must be the same.")
        sys.exit(1)

    remote_url = remote.get_remote_url()
    if remote_url is None:
        console.print("No remote URL found. Please run `lep remote login` first.")
        sys.exit(1)
    auth_token = remote.cli.get_auth_token(remote_url)
    existing_secrets = api.list_remote(remote_url, auth_token)
    for n in name:
        if n in existing_secrets:
            console.print(
                f"Secret with name {n} already exists. Please use a different name or"
                " remove the existing secret with `lep secret remove` first."
            )
            sys.exit(1)
    api.create_remote(remote_url, auth_token, name, value)
    console.print(f"Secret created successfully: {', '.join(name)}.")


@secret.command()
def list():
    remote_url = remote.get_remote_url()
    if remote_url is None:
        console.print("No remote URL found. Please run `lep remote login` first.")
        sys.exit(1)
    auth_token = remote.cli.get_auth_token(remote_url)
    secrets = api.list_remote(remote_url, auth_token)
    secrets.sort()
    table = Table(title="Secrets", show_lines=True)
    table.add_column("ID")
    table.add_column("Value")
    for secret in secrets:
        table.add_row(secret, "(hidden)")
    console.print(table)


@secret.command()
@click.option("--name", "-n", help="Secret name")
def remove(name):
    remote_url = remote.get_remote_url()
    if remote_url is None:
        console.print("No remote URL found. Please run `lep remote login` first.")
        sys.exit(1)
    auth_token = remote.cli.get_auth_token(remote_url)
    api.remove_remote(remote_url, auth_token, name)
    console.print(f"Secret deleted successfully: {name}.")


def add_command(click_group):
    click_group.add_command(secret)
