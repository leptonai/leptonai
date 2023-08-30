"""
Secret is a module that provides a way to manage secrets on a workspace.
"""

import click

from rich.table import Table

from .util import (
    console,
    check,
    click_group,
    guard_api,
    get_connection_or_die,
    explain_response,
)
from leptonai.api import secret as api
from leptonai.config import LEPTON_RESERVED_ENV_PREFIX


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
            not n.lower().startswith(LEPTON_RESERVED_ENV_PREFIX),
            "Secret name cannot start with reserved prefix"
            f" {LEPTON_RESERVED_ENV_PREFIX}. Found {n}.",
        )
    conn = get_connection_or_die()
    existing_secrets = api.list_secret(conn)
    if existing_secrets:
        for n in name:
            check(
                n not in existing_secrets,
                f"Secret with name [red]{n}[/] already exists. Please use a"
                " different name or remove the existing secret with `lep secret"
                " remove` first.",
            )
    response = api.create_secret(conn, name, value)
    explain_response(
        response,
        f"Secret created successfully: [green]{'[/], [green]'.join(name)}[/].",
        f"{response.text}\nCannot create secrets. See error message above.",
        f"{response.text}\nInternal error. See error message above.",
    )


@secret.command()
def list():
    """
    Lists all secrets in the current workspace. Note that the secret values are
    always hidden.
    """
    conn = get_connection_or_die()
    secrets = guard_api(api.list_secret(conn))
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
    conn = get_connection_or_die()
    response = api.remove_secret(conn, name)
    explain_response(
        response,
        f"Secret [green]{name}[/] deleted successfully.",
        f"Secret [yellow]{name}[/] does not exist.",
        f"{response.text}\nInternal error. See error message above.",
    )


def add_command(cli_group):
    cli_group.add_command(secret)
