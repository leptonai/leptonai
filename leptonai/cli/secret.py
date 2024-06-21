"""
Secret is a module that provides a way to manage secrets on a workspace.
"""

import click

from rich.table import Table

from .util import (
    console,
    check,
    click_group,
)
from leptonai.config import LEPTON_RESERVED_ENV_NAMES
from ..api.v1.client import APIClient
from ..api.v1.types.common import SecretItem


@click_group()
def secret():
    """
    Manage secrets on the Lepton AI cloud.

    Secrets are like environmental variables, but the actual value never leaves
    the cloud environment. Secrets can be used to store sensitive information
    like API keys and passwords, which one does not want to accidentally leak
    into display output. Secret names starting with `LEPTON_` or `lepton_` are
    reserved for system use, and cannot be used by the user.

    The secret commands allow you to create, list, and remove secrets on the
    Lepton AI cloud.
    """
    pass


@secret.command()
@click.option("--name", "-n", help="Secret name", multiple=True)
@click.option("--value", "-v", help="Secret value", multiple=True)
def create(name, value):
    """
    Creates secrets with the given name and value. The name and value can be
    specified multiple times to create multiple secrets, e.g.:
    `lep secret create -n SECRET1 -v VALUE1 -n SECRET2 -v VALUE2`
    """
    check(len(name), "No secret name given.")
    check(len(name) == len(value), "Number of names and values must be the same.")
    for n in name:
        check(
            n not in LEPTON_RESERVED_ENV_NAMES,
            "You have used a reserved secret name that is "
            "used by Lepton internally: {k}. Please use a different name. "
            "Here is a list of all reserved environment variable names:\n"
            f"{LEPTON_RESERVED_ENV_NAMES}",
        )
    client = APIClient()
    existing_secrets = client.secret.list_all()

    if existing_secrets:
        for n in name:
            check(
                n not in existing_secrets,
                f"Secret with name [red]{n}[/] already exists. Please use a"
                " different name or remove the existing secret with `lep secret"
                " remove` first.",
            )

    secret_item_list = []
    for cur_name, cur_value in zip(name, value):
        secret_item_list.append(SecretItem(name=cur_name, value=cur_value))

    client.secret.create(secret_item_list)
    console.print(
        f"Secret created successfully: [green]{'[/], [green]'.join(name)}[/]."
    )


@secret.command(name="list")
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


@secret.command()
@click.option("--name", "-n", help="Secret name")
def remove(name):
    """
    Removes the secret with the given name.
    """
    client = APIClient()
    client.secret.delete(name)
    console.print(f"Secret [green]{name}[/] deleted successfully.")


def add_command(cli_group):
    cli_group.add_command(secret)
