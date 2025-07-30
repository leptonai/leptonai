"""
Common utilities for the CLI.
"""

import sys
from typing import Any, Dict, List
from urllib.parse import urlparse

import click
from loguru import logger

from rich.console import Console
from leptonai.api.v2.client import APIClient

from leptonai.config import DASHBOARD_URL
from leptonai.api.v1.types.deployment import (
    ContainerPort,
    ContainerPortExposeStrategy,
)

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


def _get_valid_nodegroup_ids(node_groups: [str], need_queue_priority=False):
    client = APIClient()
    valid_ng = client.nodegroup.list_all()

    valid_ng_map: Dict[str, str] = {ng.metadata.name: ng for ng in valid_ng}
    node_group_ids = []
    for ng in node_groups:
        if ng not in valid_ng_map:
            console.print(
                f"Invalid node group: [red]{ng}[/] (valid node groups:"
                f" {', '.join(valid_ng_map.keys())})"
            )
            sys.exit(1)

        current_ng = valid_ng_map[ng]

        if not need_queue_priority or current_ng.status.quota_enabled is True:
            node_group_ids.append(current_ng.metadata.id_)
        else:
            console.print(
                f"[red]Warning[/red]: Node group '{ng}' does not support"
                " queue_priority."
            )

    if len(node_group_ids) == 0:
        console.print("[red]Warning[/red]: No valid node groups found.")
        sys.exit(1)

    return node_group_ids


def make_container_port_from_string(
    port_str: str, *, strategy_free: bool = False
) -> ContainerPort:
    """Parse --container-port value.

    Expected format: <port>:<protocol>:<strategy>[:strategy]
    * <port>      — integer 1-65535
    * <protocol>  — tcp | udp | sctp
    * <strategy>  — proxy | hostmap (case-insensitive)
    One or two strategies may be specified. Order is not significant beyond the first two fixed segments.
    """

    parts = [p.strip() for p in port_str.split(":")]
    # Check for empty segments
    if "" in parts:
        raise ValueError(
            f"Invalid port definition '{port_str}'. Empty segments are not allowed."
        )

    # Validate minimal segments
    if strategy_free:
        if len(parts) > 2:
            raise ValueError(
                f"Invalid port definition '{port_str}'. Expected <port>:<protocol>"
            )
        if len(parts) < 2:
            raise ValueError(
                f"Invalid port definition '{port_str}'. Expected <port>:<protocol>"
            )
    else:
        if len(parts) < 3:
            raise ValueError(
                f"Invalid port definition '{port_str}'. Expected"
                " <port>:<protocol>:<strategy>[:strategy]."
            )

    try:
        port_num = int(parts[0])
    except ValueError:
        raise ValueError(f"First segment must be an integer port, got '{parts[0]}'.")

    proto = parts[1]

    has_proxy = False
    has_host = False

    for seg in parts[2:]:
        seg_lower = seg.lower()
        if seg_lower == "proxy":
            if has_proxy:
                raise ValueError("Duplicate 'proxy' strategy in definition.")
            has_proxy = True
        elif seg_lower in {
            "hostmap",
            "host-mapping",
            "hostmapping",
            "host",
            "host-map",
        }:
            if has_host:
                raise ValueError("Duplicate 'hostmap' strategy in definition.")
            has_host = True
        else:
            raise ValueError(
                f"Unknown strategy '{seg}' in '{port_str}'. Use proxy or hostmap."
            )

    if not strategy_free and not (has_proxy or has_host):
        raise ValueError(
            "At least one exposure strategy (proxy or hostmap) must be specified."
        )

    strategies = []
    if has_proxy:
        strategies.append(ContainerPortExposeStrategy.INGRESS_PROXY)
    if has_host:
        strategies.append(ContainerPortExposeStrategy.HOST_PORT_MAPPING)

    return ContainerPort(
        name=None,
        container_port=port_num,
        protocol=proto.upper(),
        expose_strategies=strategies,
    )


def make_container_ports_from_str_list(
    port_strings: List[str], *, strategy_free: bool = False
) -> List[ContainerPort]:
    """Convert list of CLI strings to ContainerPort list, ensuring rules like single proxy."""

    parsed_ports = [
        make_container_port_from_string(p, strategy_free=strategy_free)
        for p in port_strings
    ]

    # Ensure at most one proxy across all ports
    if not strategy_free:
        proxy_count = sum(
            1
            for cp in parsed_ports
            if cp.expose_strategies
            and ContainerPortExposeStrategy.INGRESS_PROXY in cp.expose_strategies
        )
        if proxy_count > 1:
            raise ValueError(
                "Only one container port may use the 'proxy' strategy within a single"
                " job."
            )

    # Ensure no duplicate container_port numbers
    seen_ports = set()
    for cp in parsed_ports:
        if cp.container_port in seen_ports:
            raise ValueError(
                f"Duplicate container port '{cp.container_port}' detected in definition"
                " list."
            )
        seen_ports.add(cp.container_port)

    return parsed_ports


def _get_valid_node_ids(node_group_ids: [str], node_ids: [str]):
    if (
        not node_group_ids
        or len(node_group_ids) == 0
        or not node_ids
        or len(node_ids) == 0
    ):
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


def build_dashboard_job_url(workspace_id: str, job_id: str) -> str:
    """Return full dashboard URL for a given job.

    Args:
        workspace_id: Current workspace ID.
        job_id: Job's metadata.id_.

    Example output:
        https://dashboard.dgxc-lepton.nvidia.com/workspace/<ws>/compute/jobs/detail/<job>/replicas/list
    """
    return f"{DASHBOARD_URL}/workspace/{workspace_id}/compute/jobs/detail/{job_id}/replicas/list"
