"""
Common utilities for the CLI.
"""

import sys
from typing import Any, Dict
from urllib.parse import urlparse

import click
from loguru import logger

from rich.console import Console
from leptonai.api.v1.client import APIClient


console = Console(highlight=False)


def catch_deprecated_flag(old_name, new_name):
    def warn_old_name(ctx, param, value):
        if ctx.get_parameter_source(old_name) == click.core.ParameterSource.COMMANDLINE:
            console.print(
                f"[yellow]Warning:[/] Flag [yellow]--{old_name}[/] is deprecated. Use"
                f" [green]--{new_name}[/] instead."
            )
        return value

    return warn_old_name


def click_group(*args, **kwargs):
    """
    A wrapper around click.group that allows for command shorthands as long as
    they are unambiguous. For example, in the lepton case, the command `lep deployment`
    can be shortened to `lep depl` as `depl` uniquely identifies the `deployment` command.
    """

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


def check(condition: Any, message: str) -> None:
    """
    Checks a condition and prints a message if the condition is false.

    :param condition: The condition to check.
    :param message: The message to print if the condition is false.
    """
    if not condition:
        console.print(message)
        sys.exit(1)


def explain_response(response, if_2xx, if_4xx, if_others, exit_if_4xx=False):
    """
    A wrapper function that prints a message based on the response status code
    If the response status code is 2xx or 3xx, print if_2xx, and return.
    If the response status code is 4xx, print if_4xx, and exit if exit_if_4xx is true.
    If the response status code is anything else, print if_others and always exit(1).

    This is useful for apis that directly return a response object.
    """
    if response.ok or response.is_redirect:
        if if_2xx:
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


def _get_only_replica_public_ip(name: str):
    client = APIClient()
    replicas = client.deployment.get_replicas(name)
    logger.trace(f"Replicas for {name}:\n{replicas}")

    if len(replicas) != 1:
        console.print(f"Pod {name} has more than one replica. This is not supported.")
        sys.exit(1)
    return replicas[0].status.public_ip


def _get_valid_nodegroup_ids(node_groups: [str]):
    client = APIClient()
    valid_ng = client.nodegroup.list_all()
    valid_ng_map: Dict[str, str] = {ng.metadata.name: ng.metadata.id_ for ng in valid_ng}  # type: ignore
    node_group_ids = []
    for ng in node_groups:
        if ng not in valid_ng_map:
            console.print(
                f"Invalid node group: [red]{ng}[/] (valid node groups:"
                f" {', '.join(valid_ng_map.keys())})"
            )
            sys.exit(1)
        node_group_ids.append(valid_ng_map[ng])

    return node_group_ids


def _get_valid_node_ids(node_group_ids: [str], node_ids: [str]):
    if not node_group_ids or len(node_group_ids) == 0:
        return None
    node_ids_set = set(node_ids)
    client = APIClient()
    valid_nodes_id = set()
    for ng_id in node_group_ids:
        cur_all_nodes = client.nodegroup.list_nodes(name_or_ng=ng_id)
        for node in cur_all_nodes:
            if node.metadata.id_ in node_ids_set:
                valid_nodes_id.add(node.metadata.id_)
    invalid_node_ids = node_ids_set - valid_nodes_id
    if invalid_node_ids and len(invalid_node_ids) > 0:
        console.print(
            f"Invalid node ids: [red]{', '.join(invalid_node_ids)}[/]\nPlease try to"
            " use [green]'lep node list -d'[/] to check your node groups and nodes"
        )

        # We will stop this creation operation if user entered a wrong node id
        console.print(
            "[red]Creation process halted. Please enter a valid node ID and try"
            " again.[/]"
        )
        sys.exit(1)
    return valid_nodes_id
