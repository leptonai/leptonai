"""
Secret is a module that provides a way to manage secrets on a workspace.
"""

import sys

import click

from rich.table import Table

from .util import (
    single_keyword,
    console,
    err_console,
    check,
    click_group,
    LooseChoice,
    keyword_matches,
    normalize_keyword,
    state_matches,
)
from leptonai.config import LEPTON_RESERVED_ENV_NAMES
from .client import APIClient
from ..api.v2.types.common import LeptonVisibility
from ..api.v2.types.secret import SecretItem


@click_group()
def secret():
    """
    Manage secrets on the DGX Cloud Lepton.

    Secrets are like environmental variables, but the actual value never leaves
    the cloud environment. Secrets can be used to store sensitive information
    like API keys and passwords, which one does not want to accidentally leak
    into display output. Secret names starting with `LEPTON_` or `lepton_` are
    reserved for system use, and cannot be used by the user.

    The secret commands allow you to create, list, and remove secrets on the
    DGX Cloud Lepton.
    """
    pass


@secret.command()
@click.option("--name", "-n", help="Secret name", multiple=True)
@click.option("--value", "-v", help="Secret value", multiple=True)
@click.option(
    "--public-key",
    is_flag=True,
    help="Make the secret public (default is private).",
    default=False,
)
def create(name, value, public_key):
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
            f"used by Lepton internally: {n}. Please use a different name. "
            "Here is a list of all reserved environment variable names:\n"
            f"{LEPTON_RESERVED_ENV_NAMES}",
        )
    client = APIClient()
    existing_secrets = client.secret.list_all()

    if existing_secrets:
        existing_names = {s.name for s in existing_secrets}
        for n in name:
            check(
                n not in existing_names,
                f"Secret with name [red]{n}[/] already exists. Please use a"
                " different name or remove the existing secret with `lep secret"
                " remove` first.",
            )

    secret_item_list = []
    for cur_name, cur_value in zip(name, value):
        visibility = LeptonVisibility.PUBLIC if public_key else LeptonVisibility.PRIVATE
        secret_item_list.append(
            SecretItem(name=cur_name, value=cur_value, visibility=visibility)
        )

    client.secret.create(secret_item_list)
    console.print(
        f"Secret created successfully: [green]{'[/], [green]'.join(name)}[/]."
    )


SECRET_VISIBILITY_FILTER_VALUES = tuple(
    visibility.value for visibility in LeptonVisibility
)


def _filter_secrets(secrets, *, keyword=None, owners=(), visibility=None):
    """Apply the secret list filters; different filters are combined with AND."""
    normalized_keyword = normalize_keyword(keyword)
    wanted_visibility = (visibility,) if visibility else ()

    def matches(secret):
        # The dashboard filters secrets in the browser: a case-insensitive
        # substring of the name, and an exact (case-sensitive) owner match.
        if not keyword_matches(normalized_keyword, getattr(secret, "name", None)):
            return False
        if owners and (getattr(secret, "owner", None) or "") not in owners:
            return False
        return state_matches(wanted_visibility, getattr(secret, "visibility", None))

    return [secret for secret in secrets if matches(secret)]


@secret.command(name="list")
@click.option(
    "--search",
    "--keyword",
    "-q",
    "keyword",
    type=str,
    help=(
        "Search by secret name (case-insensitive substring), as the dashboard's"
        " search box does. Takes one term."
    ),
    multiple=True,
    callback=single_keyword,
)
@click.option(
    "--owner",
    "--created-by",
    "--user",
    "-u",
    "owners",
    type=str,
    multiple=True,
    help=(
        "Filter by owner, as the dashboard's creator filter does: an exact,"
        " case-sensitive match on the Owner column. Repeat for OR."
    ),
)
@click.option(
    "--visibility",
    type=LooseChoice(SECRET_VISIBILITY_FILTER_VALUES),
    help="CLI-only: show only public or only private secrets.",
)
def list_command(keyword=None, owners=(), visibility=None):
    """
    Lists all secrets in the current workspace. Note that the secret values are
    always hidden.

    --search matches the secret name or tags and --owner the owner (as in the
    dashboard); --visibility narrows to public or private secrets. Different
    filters are combined with AND.
    """
    client = APIClient()
    secrets = client.secret.list_all()
    has_filters = any([keyword, owners, visibility])
    secrets = _filter_secrets(
        secrets, keyword=keyword, owners=owners, visibility=visibility
    )
    if has_filters and not secrets:
        console.print("[yellow]No secrets match the specified filters.[/yellow]")
        return
    secrets.sort(key=lambda s: s.name)
    table = Table(title="Secrets", show_lines=True)
    table.add_column("Name")
    table.add_column("Tags")
    table.add_column("Owner")
    table.add_column("Visibility")
    for s in secrets:
        tags = ",".join(s.tags) if s.tags else ""
        owner = s.owner or ""
        visibility = s.visibility.value if getattr(s, "visibility", None) else ""
        table.add_row(s.name, tags, owner, visibility)
    console.print(table)


@secret.command()
@click.option("--name", "-n", help="Secret name", required=True)
def remove(name):
    """
    Removes the secret with the given name.
    """
    client = APIClient()
    existing_secrets = client.secret.list_all()
    existing_names = {s.name for s in existing_secrets}
    if name not in existing_names:
        # The delete API is idempotent (200 for a missing key), so this check is
        # the only place a typo surfaces; fail like the other remove commands.
        err_console.print(f"[red]Error[/]: Secret [bold]{name}[/] does not exist.")
        # Private secrets are stored as "<name>.<user>"; point at the real key.
        candidates = sorted(n for n in existing_names if n.startswith(f"{name}."))
        if candidates:
            err_console.print(
                "Did you mean "
                + " or ".join(f"[bold]{c}[/]" for c in candidates)
                + "? Private secrets are stored with a user suffix."
            )
        sys.exit(1)

    client.secret.delete(name)
    console.print(f"Secret [green]{name}[/] deleted successfully.")


def add_command(cli_group):
    cli_group.add_command(secret)
