"""
Common utilities for the CLI.
"""

import sys
from typing import Any, Optional
from urllib.parse import urlparse

import click

from rich.console import Console
from leptonai.api import APIError
from leptonai.api.connection import Connection
from leptonai.api.workspace import WorkspaceInfoLocalRecord


console = Console(highlight=False)


def click_group(*args, **kwargs):
    class ClickAliasedGroup(click.Group):
        def get_command(self, ctx, cmd_name):
            rv = click.Group.get_command(self, ctx, cmd_name)
            if rv is not None:
                return rv

            def is_abbrev(x, y):
                # first char must match
                if x[0] != y[0]:
                    return False
                it = iter(y)
                return all(any(c == ch for c in it) for ch in x)

            matches = [x for x in self.list_commands(ctx) if is_abbrev(cmd_name, x)]

            if not matches:
                return None
            elif len(matches) == 1:
                return click.Group.get_command(self, ctx, matches[0])
            ctx.fail(f"'{cmd_name}' is ambiguous: {', '.join(sorted(matches))}")

        def resolve_command(self, ctx, args):
            # always return the full command name
            _, cmd, args = super().resolve_command(ctx, args)
            return cmd.name, cmd, args

    return click.group(*args, cls=ClickAliasedGroup, **kwargs)


def is_valid_url(candidate_str: str) -> bool:
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""


def get_connection_or_die() -> Connection:
    """
    Gets the connection to the current workspace, or exits if the connection
    cannot be established.
    """
    try:
        conn = WorkspaceInfoLocalRecord.get_current_connection()
    except RuntimeError:
        console.print("It seems that you are not logged in yet.")
        sys.exit(1)
    return conn


def check(condition: Any, message: str) -> None:
    """
    Checks a condition and prints a message if the condition is false.

    :param condition: The condition to check.
    :param message: The message to print if the condition is false.
    """
    if not condition:
        console.print(message)
        sys.exit(1)


def guard_api(
    content_or_error: Any, detail: Optional[bool] = False, msg: Optional[str] = None
):
    """
    A wrapper around API calls that exits if the call  prints an error message and exits if the call was unsuccessful.

    This is useful for apis that return either a JSON response or an APIError.

    :param json_or_error: The json returned by the API call, or an APIError.
    :param detail: If True, print the error message from the API call.
    :param msg: If not None, print this message instead of the error message from the API call.
    """
    if isinstance(content_or_error, APIError):
        if detail:
            console.print(content_or_error)
        if msg:
            console.print(msg)
        sys.exit(1)
    # If the above are not true, then the API call was successful, and we can return the json.
    return content_or_error


def explain_response(response, if_2xx, if_4xx, if_others, exit_if_4xx=False):
    """
    A wrapper function that prints a message based on the response status code
    If the response status code is 2xx, print if_2xx, and return.
    If the response status code is 4xx, print if_4xx, and exit if exit_if_4xx is true.
    If the response status code is anything else, print if_others and always exit(1).

    This is useful for apis that directly return a response object.
    """
    if response.status_code >= 200 and response.status_code <= 299:
        console.print(if_2xx)
        return
    else:
        if response.status_code >= 400 and response.status_code <= 499:
            errmsg = if_4xx
        else:
            errmsg = if_others
        try:
            # convert response text to json
            content = response.json()
            console.print(
                f"{response.status_code} {content['code']}:"
                f" {content['message']}\n{errmsg}"
            )
        except Exception:
            # fallback to display raw message
            console.print(f"{response.status_code}: {response.text}\n{errmsg}")

        if (
            response.status_code >= 400
            and response.status_code <= 499
            and not exit_if_4xx
        ):
            return
        else:
            sys.exit(1)


def sizeof_fmt(num, suffix="B"):
    """
    Convert a quantity of bytes to a human readable format.
    ref: https://web.archive.org/web/20111010015624/http://blogmag.net/blog/read/38/Print_human_readable_file_size
    """
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
