from collections import defaultdict
from datetime import datetime
import re

import click
from rich.table import Table

from .util import (
    console,
    check,
    click_group,
    guard_api,
    get_workspace_and_token_or_die,
    explain_response,
)
from leptonai.api import deployment as api


@click_group()
def deployment():
    """
    Manage deployments on the Lepton AI cloud.

    Deployment is a running instance of a photon. Deployments are created using
    the `lep photon run` command. Usually, a deployment exposes one or more HTTP
    endpoints that the users call, either via a RESTful API, or a python client
    defined in `leptonai.client`.

    The deployment commands allow you to list, manage, and remove deployments on
    the Lepton AI cloud.
    """
    pass


@deployment.command()
@click.option(
    "--pattern",
    "-p",
    help="Regular expression pattern to filter deployment names.",
    default=None,
)
def list(pattern):
    """
    Lists all deployments in the current workspace.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    deployments = guard_api(
        api.list_deployment(workspace_url, auth_token),
        detail=True,
        msg="Cannot list deployments. See error message above.",
    )
    records = [
        (d["name"], d["photon_id"], d["created_at"] / 1000, d["status"])
        for d in deployments
    ]
    if len(records) == 0:
        console.print(
            "No deployments found. Use `lep photon run` to create deployments."
        )
        return 0

    table = Table(title="deployments", show_lines=True)
    table.add_column("name")
    table.add_column("photon id")
    table.add_column("created at")
    table.add_column("status")
    table.add_column("endpoint", overflow="fold")
    for name, photon_id, created_at, status in records:
        if pattern is not None and not re.search(pattern, name):
            continue
        table.add_row(
            name,
            photon_id,
            datetime.fromtimestamp(created_at).strftime("%Y-%m-%d\n%H:%M:%S"),
            status["state"],
            status["endpoint"]["external_endpoint"],
        )
    console.print(table)
    return 0


@deployment.command()
@click.option("--name", "-n", help="The deployment name to remove.", required=True)
def remove(name):
    """
    Removes a deployment.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    response = api.remove_deployment(workspace_url, auth_token, name)
    explain_response(
        response,
        f"Deployment [green]{name}[/] removed.",
        f"Deployment [yellow]{name}[/] does not exist.",
        f"{response.text}\nFailed to remove deployment [red]{name}[/]. See error"
        " message above.",
    )
    return 0


@deployment.command()
@click.option("--name", "-n", help="The deployment name to get status.", required=True)
def status(name):
    """
    Gets the status of a deployment.
    """
    check(name, "Deployment name not specified. Use `lep deployment status -n <name>`.")
    workspace_url, auth_token = get_workspace_and_token_or_die()

    dep_info = guard_api(
        api.get_deployment(workspace_url, auth_token, name),
        detail=True,
        msg=f"Cannot obtain info for [red]{name}[/]. See error above.",
    )
    # todo: print a cleaner dep info.
    creation_time = datetime.fromtimestamp(dep_info["created_at"] / 1000).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    state = dep_info["status"]["state"]
    if state == "Running":
        state = f"[green]{state}[/]"
    else:
        state = f"[yellow]{state}[/]"
    console.print(f"Created at: {creation_time}")
    console.print(f"Photon ID:  {dep_info['photon_id']}")
    console.print(f"State:      {state}")
    console.print(f"Endpoint:   {dep_info['status']['endpoint']['external_endpoint']}")
    console.print("Replicas:")

    rep_info = guard_api(
        api.get_readiness(workspace_url, auth_token, name),
        detail=True,
        msg=f"Cannot obtain replica info for [red]{name}[/]. See error above.",
    )
    # Print a table of readiness information.
    table = Table(show_lines=False)
    table.add_column("replica id")
    table.add_column("status")
    table.add_column("message")
    ready_count = 0
    for id, value in rep_info.items():
        reason = value[0]["reason"]
        message = value[0]["message"]
        # Do we need to display red?
        if reason == "Ready":
            reason = f"[green]{reason}[/]"
            ready_count += 1
        else:
            reason = f"[yellow]{reason}[/]"
        if message == "":
            message = "(empty)"
        table.add_row(id, reason, message)
    console.print(table)
    console.print(f"[green]{ready_count}[/] out of {len(rep_info)} replicas ready.")


@deployment.command()
@click.option("--name", "-n", help="The deployment name to get log.", required=True)
@click.option("--replica", "-r", help="The replica name to get log.", default=None)
def log(name, replica):
    """
    Gets the log of a deployment. If `replica` is not specified, the first replica
    is selected. Otherwise, the log of the specified replica is shown. To get the
    list of replicas, use `lep deployment status`.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    if not replica:
        # obtain replica information, and then select the first one.
        console.print(
            f"Replica name not specified for [yellow]{name}[/]. Selecting the first"
            " replica."
        )
        replicas = guard_api(
            api.get_replicas(workspace_url, auth_token, name),
            detail=True,
            msg=f"Cannot obtain replica info for [red]{name}[/]. See error above.",
        )
        check(len(replicas) > 0, f"No replicas found for [red]{name}[/].")
        replica = replicas[0]["id"]
        console.print(f"Selected replica [green]{replica}[/].")
    else:
        console.print(f"Showing log for replica [green]{replica}[/].")
    stream_or_err = guard_api(
        api.get_log(workspace_url, auth_token, name, replica),
        detail=False,
        msg="Cannot obtain log for [red]{replica}[/]. See error above.",
    )
    # Print the log as a continuous stream until the user presses Ctrl-C.
    try:
        for chunk in stream_or_err:
            console.print(chunk, end="")
    except KeyboardInterrupt:
        console.print("Disconnected.")
    except Exception:
        console.print("Connection stopped.")
        return


@deployment.command()
@click.option("--name", "-n", help="The deployment name to update.", required=True)
@click.option(
    "--replica",
    "-r",
    help="The number of replicas to update to.",
    type=int,
    default=None,
)
def update(name, replica):
    """
    Updates a deployment. Currently, only adjustment of the number of replicas is
    supported.
    """
    check(replica is not None, "Number of replicas not specified.")
    check(replica > 0, f"Invalid number of replicas: {replica}")
    # Just to avoid stupid errors right now, we will limit the number of replicas
    # to 100 for now.
    check(replica <= 100, f"Invalid number of replicas: {replica}")
    workspace_url, auth_token = get_workspace_and_token_or_die()
    guard_api(
        api.update_deployment(workspace_url, auth_token, name, replica),
        detail=True,
        msg=f"Cannot update deployment [red]{name}[/]. See error above.",
    )
    console.print(
        f"Deployment [green]{name}[/] updated to replica=[green]{replica}[/]."
    )


@deployment.command()
@click.option("--name", "-n", help="The deployment name.", required=True)
@click.option("--by-path", "-p", is_flag=True, help="Show detailed QPS info by path.")
def qps(name, by_path):
    """
    Gets the QPS of a deployment.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    qps_info = guard_api(
        api.get_qps(workspace_url, auth_token, name, by_path=by_path),
        detail=True,
        msg=f"Cannot obtain QPS info for [red]{name}[/]. See error above.",
    )
    if len(qps_info) == 0:
        console.print(f"No QPS info found for [yellow]{name}[/].")
        return
    if by_path:
        all_paths = [p["metric"]["handler"] for p in qps_info]
        all_paths = sorted(all_paths)
        table = Table(title=f"QPS of [green]{name}[/] per path", show_lines=False)
        table.add_column("time")
        for path in all_paths:
            table.add_column(path)
        value_path_speed_map = defaultdict(defaultdict)
        for path_info in qps_info:
            handler = path_info["metric"]["handler"]
            values = path_info["values"]
            for time, value in values:
                value_path_speed_map[time][handler] = value
        ordered_time = value_path_speed_map.keys()
        ordered_time = sorted(ordered_time)
        for time in ordered_time:
            row = [datetime.fromtimestamp(time).strftime("%H:%M:%S")]
            for path in all_paths:
                row.append(f"{value_path_speed_map[time][path]:.4f}")
            table.add_row(*row)
        console.print(table)
    else:
        # Print a table of QPS information.
        table = Table(title=f"QPS of [green]{name}[/]", show_lines=False)
        table.add_column("time")
        table.add_column("qps")
        content = qps_info[0]["values"]
        for time, qps in content:
            table.add_row(
                datetime.fromtimestamp(time).strftime("%H:%M:%S"), f"{qps:.4f}"
            )
        console.print(table)


@deployment.command()
@click.option("--name", "-n", help="The deployment name.", required=True)
@click.option("--by-path", "-p", is_flag=True, help="Show detailed QPS info by path.")
def latency(name, by_path):
    """
    Gets the latency of a deployment.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    latency_info = guard_api(
        api.get_latency(workspace_url, auth_token, name, by_path=by_path),
        detail=True,
        msg=f"Cannot obtain latency info for [red]{name}[/]. See error above.",
    )
    if len(latency_info) == 0:
        console.print(f"No latency info found for [yellow]{name}[/].")
        return
    if by_path:
        all_paths = [p["metric"]["handler"] for p in latency_info]
        all_paths = sorted(all_paths)
        table = Table(show_lines=False)
        table.add_column("time")
        for path in all_paths:
            table.add_column(path)
        value_path_speed_map = defaultdict(defaultdict)
        for path_info in latency_info:
            handler = path_info["metric"]["handler"]
            values = path_info["values"]
            for time, value in values:
                value_path_speed_map[time][handler] = value
        ordered_time = value_path_speed_map.keys()
        ordered_time = sorted(ordered_time)
        for time in ordered_time:
            row = [datetime.fromtimestamp(time).strftime("%H:%M:%S")]
            for path in all_paths:
                row.append(f"{value_path_speed_map[time][path]*1000:.2f}")
            table.add_row(*row)
        console.print(f"Latency (ms) of [green]{name}[/] per path")
        console.print(table)
    else:
        # Print a table of latency information.
        table = Table(show_lines=False)
        table.add_column("time")
        table.add_column("latency")
        content = latency_info[0]["values"]
        for time, latency in content:
            table.add_row(
                datetime.fromtimestamp(time).strftime("%H:%M:%S"), f"{latency*1000:.4f}"
            )
        console.print(f"Latency (ms) of [green]{name}[/]")
        console.print(table)


def add_command(cli_group):
    cli_group.add_command(deployment)
