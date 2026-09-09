"""
Common utilities for the CLI.
"""

import os
import re
import sys
import traceback
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import click
from loguru import logger
from leptonai.api.v2.api_resource import ClientError, ServerError
from leptonai.api.v2.utils import WorkspaceError, WorkspaceConfigurationError

from rich.console import Console
from leptonai.api.v2.types.job import LeptonJob, LeptonJobQueryMode
from leptonai.api.v2.client import APIClient

from leptonai.api.v2.types.deployment import (
    ContainerPort,
    ContainerPortExposeStrategy,
)

console = Console(highlight=False)


class PathResolutionError(Exception):
    """Raised when preparing target directory for save path fails."""

    def __init__(self, directory: str, cause: Exception):
        super().__init__(f"failed to create directory: {directory} ({cause})")
        self.directory = directory
        self.cause = cause


def resolve_save_path(path: str, default_filename: str) -> str:
    """Resolve a final file path to save to, creating directory if needed.

    Rules:
    - Treat input as directory if:
      * it is an existing directory, or
      * it ends with os.sep, or
      * it does not exist AND has no file extension
    - Otherwise treat input as a file path.
    - Create the target directory if it does not exist.
    - Return the final file path (directory joined with default_filename when needed).

    Raises:
        PathResolutionError: when directory creation fails.
    """
    # Determine whether the given path should be treated as a directory
    is_dir_like = (
        os.path.isdir(path)
        or path.endswith(os.sep)
        or (not os.path.exists(path) and not os.path.splitext(path)[1])
    )

    # Normalize the target directory to avoid issues with trailing separators
    target_dir = os.path.normpath(path) if is_dir_like else os.path.dirname(path)

    # Create directory if needed
    if target_dir and not os.path.exists(target_dir):
        try:
            os.makedirs(target_dir)
        except Exception as e:
            raise PathResolutionError(target_dir, e)

    # Construct final path
    final_path = os.path.join(target_dir, default_filename) if is_dir_like else path
    return final_path


def catch_deprecated_flag(old_name, new_name):
    def warn_old_name(ctx, param, value):
        if ctx.get_parameter_source(old_name) == click.core.ParameterSource.COMMANDLINE:
            console.print(
                f"[yellow]Warning:[/] Flag [yellow]--{old_name}[/] is deprecated. Use"
                f" [green]--{new_name}[/] instead."
            )
        return value

    return warn_old_name


class _ValidatedCommand(click.Command):
    """Global guard: forbid empty or whitespace-only string values from CLI.

    This validates only values provided from COMMANDLINE source, and supports
    both single-value and multiple=True options. It does not change default
    values or environment-derived values.
    """

    def invoke(self, ctx):
        def _is_blank_str(v):
            return isinstance(v, str) and v.strip() == ""

        for param_name, param_value in ctx.params.items():
            # Only enforce for values explicitly provided on the command line
            try:
                src = ctx.get_parameter_source(param_name)
            except Exception:
                src = None
            if src != click.core.ParameterSource.COMMANDLINE:
                continue

            # Single string value
            if _is_blank_str(param_value):
                param_obj = next(
                    (p for p in self.params if getattr(p, "name", None) == param_name),
                    None,
                )
                msg = (
                    "must not be empty or only whitespace. Omit the flag instead of"
                    " passing an empty string."
                )
                if param_obj is not None:
                    raise click.BadParameter(msg, param=param_obj)
                ctx.fail(f"Option '--{param_name}' {msg}")

            # Multiple values
            if isinstance(param_value, (list, tuple)) and any(
                _is_blank_str(x) for x in param_value
            ):
                param_obj = next(
                    (p for p in self.params if getattr(p, "name", None) == param_name),
                    None,
                )
                msg = "contains empty value(s). Remove empty items."
                if param_obj is not None:
                    raise click.BadParameter(msg, param=param_obj)
                ctx.fail(f"Option '--{param_name}' {msg}")

        return super().invoke(ctx)


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

        def command(self, *c_args, **c_kwargs):
            # Ensure all commands under this group use the empty-string guard by default
            if "cls" not in c_kwargs:
                c_kwargs["cls"] = _ValidatedCommand
            return super().command(*c_args, **c_kwargs)

        def group(self, *g_args, **g_kwargs):
            # Ensure nested groups also inherit this group's behavior
            if "cls" not in g_kwargs:
                g_kwargs["cls"] = ClickAliasedGroup
            return super().group(*g_args, **g_kwargs)

        def invoke(self, ctx):
            try:
                return super().invoke(ctx)
            except WorkspaceConfigurationError as e:
                console.print(f"[red]Workspace configuration error[/]: {e}")
                sys.exit(1)
            except WorkspaceError as e:
                console.print(f"[red]{e.__class__.__name__}[/]: {e}")
                sys.exit(1)
            except ClientError as e:
                resp = getattr(e, "response", None)
                status = getattr(resp, "status_code", None)
                text = getattr(resp, "text", str(e))
                if status == 401:
                    console.print(
                        f"\n[red]401 Unauthorized[/]: {text}\n\n[yellow]Hint:[/yellow]"
                        " This may be caused by an invalid or mismatched workspace"
                        " token.\n[white] \n Check your local workspace info and"
                        " token:[/white]\n [dim]lep workspace list[/dim]\n [dim]lep"
                        " workspace token[/dim]\nGenerate a new token in your"
                        " workspace dashboard, then login again with lep login -c"
                        " <workspace_id>:<new_token>.\n"
                    )
                elif status == 403:
                    console.print(
                        f"\n[red]403 Forbidden[/]: {text}\n\n[yellow]Hint:[/yellow]"
                        " This may be caused by insufficient permissions or an expired"
                        " workspace token.\n\n[white]Check your local workspace info"
                        " and token:[/white]\n [dim]lep workspace list[/dim]\n"
                        " [dim]lep workspace token[/dim]\nIf your token has expired,"
                        " generate a new token in the workspace dashboard, then login"
                        " again with `lep login -c <workspace_id>:<new_token>`.\n"
                    )
                elif status == 404:
                    console.print(f"[red]404 Not Found[/]:{text}")
                else:
                    console.print(f"[red]{status} Error[/]: {text}")
                sys.exit(1)
            except ServerError as e:
                resp = getattr(e, "response", None)
                status = getattr(resp, "status_code", None)
                text = getattr(resp, "text", str(e))
                console.print(f"[red]{status} Error[/]: {text}")
                sys.exit(1)
            except (click.ClickException, click.exceptions.Exit):
                raise
            except ValueError as e:
                console.print(f"[red]Error[/]: {e}")
                logger.trace(traceback.format_exc())
                sys.exit(1)
            except Exception as e:
                console.print(f"[red]Unexpected error[/]: {e}")
                console.print(traceback.format_exc())
                sys.exit(1)

    return click.group(*args, cls=ClickAliasedGroup, **kwargs)


def is_valid_url(candidate_str: str) -> bool:
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""


# Singleton API client for CLI process
_client_singleton: Optional[APIClient] = None


def get_client() -> APIClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = APIClient()
    return _client_singleton


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


def _get_only_replica_public_ip(name: str, client: Optional[APIClient] = None):
    # Reuse the caller's client when provided so this helper shares the caller's
    # dispatch decision. The dispatch flag is committed process-wide on first
    # resolution (client.py), so even the get_client() fallback below now agrees
    # with the caller; passing the caller's client remains the clearer contract.
    if client is None:
        client = get_client()
    # The new devpod API exposes no /replicas route; the single pod's public IP
    # is surfaced directly on the devpod status as a bare IP (status.public_ip),
    # carried through by the response translation. In legacy mode, read it from
    # the single replica as before. The dispatch flag is stable process-wide, so
    # this branch cannot disagree with the caller's pod routing.
    if client.new_deployment_api_enabled:
        pod = client.pod.get(name)
        status = pod.status
        return status.public_ip if status else None
    replicas = client._deployment_api_for_legacy_pod().get_replicas(name)
    logger.trace(f"Replicas for {name}:\n{replicas}")

    if len(replicas) != 1:
        console.print(f"Pod {name} has more than one replica. This is not supported.")
        sys.exit(1)
    return replicas[0].status.public_ip


def _get_valid_nodegroup_ids(node_groups: [str], need_queue_priority=False):
    client = get_client()
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


def resolve_node_groups(node_group_terms: List[str], is_exact_match: bool = False):
    client = get_client()
    node_groups = client.nodegroup.list_all()
    filtered_node_groups = node_groups
    if node_group_terms:
        filtered_node_groups = find_matching_node_groups(
            list(node_group_terms), node_groups, is_exact_match=is_exact_match
        )

    if len(filtered_node_groups) == 0:
        phrase = (
            "with name/id equal to" if is_exact_match else "with name/id containing"
        )
        terms_str = ", ".join(f"[bold]{t}[/bold]" for t in node_group_terms)
        avail_str = ", ".join(
            sorted(f"{ng.metadata.name} ({ng.metadata.id_})" for ng in node_groups)
        )
        console.print(
            f"[yellow]Warning:[/yellow] No node groups {phrase} {terms_str}.\n"
            f"Available node groups: {avail_str}"
        )
    return filtered_node_groups


def find_matching_node_groups(
    terms: List[str], all_node_groups=None, *, is_exact_match: bool = False
):
    """Return node groups whose id or name matches any of given terms.

    - terms: patterns to match (empty -> empty result)
    - all_node_groups: optional pre-fetched list to search; if None, fetch all
    - is_exact_match: if True, require exact id/name match; otherwise substring match
    - preserves original order; de-duplicates by node group id
    """
    if not terms:
        return []
    if not all_node_groups:
        client = get_client()
        all_node_groups = client.nodegroup.list_all()

    seen_ids = set()
    matches = []
    for ng in all_node_groups:
        if is_exact_match:
            ok = any((t == ng.metadata.id_) or (t == ng.metadata.name) for t in terms)
        else:
            ok = any((t in ng.metadata.id_) or (t in ng.metadata.name) for t in terms)
        if ok:
            if ng.metadata.id_ in seen_ids:
                continue
            seen_ids.add(ng.metadata.id_)
            matches.append(ng)
    return matches


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
    client = get_client()
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


def _get_newest_job_by_name(
    job_name: str, job_query_mode: str = LeptonJobQueryMode.AliveOnly.value
) -> LeptonJob:
    """
    Resolve the newest job by exact name under the given query mode.
    Returns the newest LeptonJob or None if no exact match.
    """
    client = get_client()
    job_list = client.job.list_all(job_query_mode=job_query_mode, q=job_name)
    exact_matches = [j for j in job_list if j.metadata.name == job_name]
    if not exact_matches:
        return None
    return max(exact_matches, key=lambda j: j.metadata.created_at)


def _validate_queue_priority(ctx, param, value):
    """Validate and normalize --queue-priority.

    Accepted input examples: low / l / low-1, mid / 5, high-9, 7, mid-4000.
    Always returns canonical strings such as 'mid-4000'.
    """

    if value is None:
        return value

    canonical = {
        "l": "low-1000",
        "low": "low-1000",
        "low-1": "low-1000",
        "low-2": "low-2000",
        "low-3": "low-3000",
        "m": "mid-4000",
        "mid": "mid-4000",
        "mid-4": "mid-4000",
        "mid-5": "mid-5000",
        "mid-6": "mid-6000",
        "h": "high-7000",
        "high": "high-7000",
        "high-7": "high-7000",
        "high-8": "high-8000",
        "high-9": "high-9000",
    }

    # allow direct canonical strings
    canonical.update({v: v for v in canonical.values()})

    numeric_map = {
        1: "low-1000",
        2: "low-2000",
        3: "low-3000",
        4: "mid-4000",
        5: "mid-5000",
        6: "mid-6000",
        7: "high-7000",
        8: "high-8000",
        9: "high-9000",
    }

    if isinstance(value, str):
        v = value.lower()
        if v in canonical:
            return canonical[v]

    try:
        num = int(value)
        if 1 <= num <= 9:
            return numeric_map[num]
    except (TypeError, ValueError):
        pass

    opts = ", ".join(
        sorted(set(list(canonical.keys()) + [str(n) for n in numeric_map]))
    )
    raise ValueError(f"invalid priority '{value}'. valid options: {opts}")


def apply_nodegroup_and_queue_config(
    *,
    spec,
    node_groups,
    node_ids,
    queue_priority,
    can_be_preempted,
    can_preempt,
    with_reservation,
    allow_burst,
):
    """Mutate *spec* to attach affinity / QueueConfig / ReservationConfig.

    Raises ValueError when required dedicated node group info is missing."""

    from leptonai.api.v2.types.affinity import LeptonResourceAffinity
    from leptonai.api.v2.types.deployment import QueueConfig, ReservationConfig

    # Determine flags presence
    has_queue_flags = (
        queue_priority is not None
        or can_be_preempted is not None
        or can_preempt is not None
    )
    has_reservation_flags = bool(with_reservation or allow_burst)

    if hasattr(spec, "affinity"):
        holder = spec
    else:
        # Deployment/Pod-style spec – resource_requirement must exist beforehand
        if getattr(spec, "resource_requirement", None) is None:
            raise ValueError(
                "for endpoint_user_spec, resource_requirement must be set before"
                " applying node group / queue / reservation flags."
            )
        holder = spec.resource_requirement

    # Step 1: node group handling
    if node_groups:
        node_group_ids = _get_valid_nodegroup_ids(
            node_groups, need_queue_priority=has_queue_flags
        )
        valid_node_ids = (
            _get_valid_node_ids(node_group_ids, node_ids) if node_ids else None
        )

        holder.affinity = LeptonResourceAffinity(
            allowed_dedicated_node_groups=node_group_ids,
            allowed_nodes_in_node_group=valid_node_ids,
        )

    elif has_queue_flags or has_reservation_flags:
        affinity = getattr(holder, "affinity", None)
        enabled = affinity and affinity.allowed_dedicated_node_groups
        if not enabled:
            raise ValueError(
                "queue/preempt/reservation flags require --node-group (dedicated node"
                " group)."
            )

    if has_queue_flags:
        spec.queue_config = spec.queue_config or QueueConfig()
        spec.queue_config.priority_class = queue_priority or "mid-4000"
        if can_be_preempted is not None:
            spec.queue_config.can_be_preempted = can_be_preempted
        if can_preempt is not None:
            spec.queue_config.can_preempt = can_preempt

    if has_reservation_flags:
        spec.reservation_config = spec.reservation_config or ReservationConfig()
        if with_reservation:
            spec.reservation_config.reservation_id = with_reservation
        if allow_burst:
            spec.reservation_config.allow_burst_to_other_reservations = True

    return spec


def format_timestamp_ms(ms: Optional[int]) -> str:
    """Format millisecond epoch to 'YYYY-MM-DD\nHH:MM:SS'."""
    if not ms:
        return "N/A"
    from datetime import datetime

    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d\n%H:%M:%S")
    except Exception:
        return "N/A"


def _stringify_state(state: Optional[Union[str, Any]]) -> str:
    """Extract string from enum or plain string; fall back to '-'."""
    if state is None:
        return "-"
    value = getattr(state, "value", state)
    return str(value)


def colorize_state(state: Optional[Union[str, Any]]) -> str:
    """Return rich-markup colored state string.

    Green for healthy/success states (Ready/Running/Completed), red for failure
    states (Error/Failed), yellow for any other non-empty transitional state.
    """
    text = _stringify_state(state)
    if text in {"Ready", "Running", "Completed"}:
        return f"[green]{text}[/]"
    if text in {"Error", "Failed"}:
        return f"[red]{text}[/]"
    return f"[yellow]{text}[/]" if text and text != "-" else "-"


def make_name_id_cell(
    name: Optional[str],
    id_: Optional[str],
    *,
    link: Optional[str] = None,
    link_target: str = "id",
) -> str:
    """Construct a two-line 'Name / ID' cell with optional link on ID or name.

    - Name is bold green (nvidia green #76b900)
    - ID is dim; if link provided, wrap ID with link markup
    - If no ID, show only name
    - If link provided but no ID, we will link the name instead
    """
    safe_name = name or "-"
    safe_id = id_ or ""
    name_markup = f"[bold #76b900]{safe_name}[/]"
    if link and safe_id and link_target == "id":
        id_markup = f"[link={link}][bright_black]{safe_id}[/][/link]"
    elif link and link_target == "name":
        # link the name when ID is missing
        name_markup = f"[link={link}]{name_markup}[/link]"
        id_markup = ""
    else:
        id_markup = f"[bright_black]{safe_id}[/]" if safe_id else ""

    return name_markup if not id_markup else f"{name_markup}\n{id_markup}"


# ---------------------------------------------------------------------------
# Shared list-filter helpers.
#
# The `lep <resource> list` commands mirror the web dashboard's filter bar: a
# free-text search (case-insensitive substring), multi-select state filters
# (exact, OR within the option) and creator filters. Different options are
# combined with AND. These helpers keep the semantics identical across the
# resource modules.
# ---------------------------------------------------------------------------


def _fold_choice(value: Any) -> str:
    """Collapse case, whitespace, hyphens and underscores for loose matching."""
    return re.sub(r"[\s_-]+", "", str(value)).casefold()


class LooseChoice(click.Choice):
    """A click.Choice that tolerates casing, spaces, hyphens and underscores.

    State names on the platform mix styles ("Not Ready", "PendingRetry",
    "ready-to-repair"), so ``--state notready``, ``--state not-ready`` and
    ``--state "Not Ready"`` all resolve to the canonical ``"Not Ready"``.
    Invalid values fail with the standard click message listing the canonical
    choices.
    """

    def __init__(self, choices):
        super().__init__(list(choices), case_sensitive=False)
        self._canonical_by_fold = {_fold_choice(c): c for c in self.choices}

    def convert(self, value, param, ctx):
        if value in self.choices:
            return value
        canonical = self._canonical_by_fold.get(_fold_choice(value))
        if canonical is None:
            choices = ", ".join(repr(c) for c in self.choices)
            self.fail(f"{value!r} is not one of {choices}.", param, ctx)
        return canonical

    def get_metavar(self, param, ctx=None):
        # Show the canonical spellings in --help; click would otherwise print
        # the case-folded forms for a case-insensitive Choice.
        choices_str = "|".join(str(c) for c in self.choices)
        if (
            getattr(param, "required", False)
            and getattr(param, "param_type_name", "") == "argument"
        ):
            return f"{{{choices_str}}}"
        return f"[{choices_str}]"


def normalize_keyword(keyword: Optional[str]) -> str:
    """Normalize a free-text search term; empty/None means "no filter"."""
    return keyword.strip().lower() if keyword else ""


def keyword_matches(keyword: str, *candidates: Any) -> bool:
    """Case-insensitive substring match of ``keyword`` against any candidate.

    ``keyword`` must already be normalized with :func:`normalize_keyword`; an
    empty keyword matches everything. ``None`` candidates are skipped.
    """
    if not keyword:
        return True
    return any(
        keyword in str(candidate).lower()
        for candidate in candidates
        if candidate is not None
    )


def prefix_matches(value: Any, prefixes) -> bool:
    """Case-insensitive prefix match of ``value`` against any of ``prefixes``.

    An empty ``prefixes`` collection matches everything (no filter).
    """
    if not prefixes:
        return True
    text = str(value).lower() if value is not None else ""
    return any(text.startswith(str(prefix).lower()) for prefix in prefixes)


def state_matches(wanted, *states: Any) -> bool:
    """Whether any of ``states`` (enum or str) is in the ``wanted`` collection.

    An empty ``wanted`` collection matches everything (no filter). Comparison
    is on the canonical state string, case-insensitively.
    """
    if not wanted:
        return True
    wanted_lower = {str(getattr(w, "value", w)).lower() for w in wanted}
    return any(
        _stringify_state(state).lower() in wanted_lower
        for state in states
        if state is not None
    )


def creator_matches(metadata: Any, creators) -> bool:
    """Match ``creators`` (case-insensitive prefixes) against a resource's creator.

    The dashboard filters on ``metadata.created_by``; ``metadata.owner`` is
    accepted as well because that is what the CLI tables display.
    """
    if not creators:
        return True
    created_by = getattr(metadata, "created_by", None) if metadata else None
    owner = getattr(metadata, "owner", None) if metadata else None
    return prefix_matches(created_by, creators) or prefix_matches(owner, creators)


def node_group_matches(affinity: Any, node_group_terms) -> bool:
    """Case-insensitive substring match against the allowed dedicated node groups."""
    if not node_group_terms:
        return True
    node_groups = (
        getattr(affinity, "allowed_dedicated_node_groups", None) if affinity else None
    ) or []
    return any(
        str(term).lower() in str(node_group).lower()
        for term in node_group_terms
        for node_group in node_groups
    )


def labels_to_selector(labels, base_query: Optional[str] = None) -> Optional[str]:
    """Build a label selector from repeatable ``--label`` values.

    Each value is ``KEY`` (label must exist), ``KEY=VALUE`` or ``KEY:VALUE``
    (the dashboard's spelling; the first ':' becomes '='). Values that already
    look like selector expressions are passed through. Entries are ANDed by
    joining them with ',' as the label-selector grammar requires, together with
    an optional raw ``base_query`` selector.
    """
    parts = []
    if base_query and base_query.strip():
        parts.append(base_query.strip())
    for label in labels or ():
        label = str(label).strip()
        if not label:
            continue
        if any(token in label for token in ("=", "!", "(", " ")):
            parts.append(label)
        elif ":" in label:
            key, _, value = label.partition(":")
            parts.append(f"{key}={value}")
        else:
            parts.append(label)
    return ",".join(parts) if parts else None
