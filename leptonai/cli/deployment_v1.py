from datetime import datetime
import re
import sys
from typing import Optional, List

import click
from rich.table import Table

from .util import (
    console,
    check,
    click_group,
)
from leptonai.api.workspace import WorkspaceInfoLocalRecord
from leptonai.config import LEPTON_DEPLOYMENT_URL
from ..api.v1.client import APIClient
from ..api.v1.types.common import Metadata
from ..api.v1.types.deployment import LeptonDeployment
from ..api.v1.types.deployment_operator_v1alpha1.deployment import (
    LeptonDeploymentUserSpec,
    ResourceRequirement,
    ScaleDown,
    AutoScaler,
    TokenVar,
    TokenValue,
)


def make_token_vars_from_config(
    is_public: Optional[bool], tokens: Optional[List[str]]
) -> Optional[List[TokenVar]]:
    # Note that None is different from [] here. None means that the tokens are not
    # changed, while [] means that the tokens are cleared (aka, public deployment)
    if is_public is None and tokens is None:
        return None
    elif is_public and tokens:
        raise ValueError(
            "For access control, you cannot specify both is_public and token at the"
            " same time. Please specify either is_public=True with no tokens passed"
            " in, or is_public=False and tokens as a list."
        )
    else:
        if is_public:
            return []
        else:
            final_tokens = [
                TokenVar(value_from=TokenValue(token_name_ref="WORKSPACE_TOKEN"))
            ]
            if tokens:
                final_tokens.extend([TokenVar(value=token) for token in tokens])
            return final_tokens


@click_group()
def deployment_v1():
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


@deployment_v1.command(name="list")
@click.option(
    "--pattern",
    "-p",
    help="Regular expression pattern to filter deployment names.",
    default=None,
)
def list_command(pattern):
    """
    Lists all deployments in the current workspace.
    """

    client = APIClient()

    deployments = client.deployment.list_all()
    # For the photon id field, we will show either the photon id, or the container
    # image name if the deployment is an arbitrary container.
    # Note: for pods, we will not show them here.
    records = [
        (
            (d.metadata.name),
            (
                d.spec.photon_id
                if d.spec.photon_id is not None
                else (d.spec.container.image or "（unknown）")
            ),
            d.metadata.created_at / 1000,
            d.status,
        )
        for d in deployments
        if not (d.spec.is_pod or False)
    ]
    if len(records) == 0:
        console.print(
            "No deployments found. Use `lep photon run` to create deployments."
        )
        return 0

    table = Table(
        title="deployments",
        show_lines=True,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("name")
    table.add_column("photon id")
    table.add_column("created at")
    table.add_column("status")
    for name, photon_id, created_at, status in records:
        if pattern is not None and not re.search(pattern, name):
            continue
        table.add_row(
            name,
            photon_id,
            datetime.fromtimestamp(created_at).strftime("%Y-%m-%d\n%H:%M:%S"),
            status.state,
        )
    console.print(table)
    return 0


@deployment_v1.command()
@click.option("--name", "-n", help="The deployment name to remove.", required=True)
def remove(name):
    """
    Removes a deployment.
    """
    client = APIClient()
    client.deployment.delete(name)
    console.print(f"Job [green]{name}[/] deleted successfully.")


@deployment_v1.command()
@click.option("--name", "-n", help="The deployment name to get status.", required=True)
@click.option(
    "--show-tokens",
    "-t",
    is_flag=True,
    help=(
        "Show tokens for the deployment. Use with caution as this displays the tokens"
        " in plain text, and may be visible to others if you log the output."
    ),
)
def status(name, show_tokens):
    """
    Gets the status of a deployment.
    """
    check(name, "Deployment name not specified. Use `lep deployment status -n <name>`.")

    client = APIClient()

    dep_info = client.deployment.get(name)
    workspace_id = client.workspace_id

    # todo: print a cleaner dep info.
    creation_time = datetime.fromtimestamp(
        dep_info.metadata.created_at / 1000
    ).strftime("%Y-%m-%d %H:%M:%S")

    state = dep_info.status.state
    if state in ("Running", "Ready"):
        state = f"[green]{state}[/]"
    else:
        state = f"[yellow]{state}[/]"
    console.print(f"Time now:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(f"Created at: {creation_time}")

    photon_id = "unknow"
    if dep_info.spec.photon_id is not None:
        photon_id = dep_info.spec.photon_id
    else:
        photon_id = (
            (dep_info.spec.container.image or "unknow")
            if dep_info.spec.container
            else "unknow"
        )

    console.print("Photon ID: ", photon_id)

    console.print(f"State:      {state}")

    resource_requirement = dep_info.spec.resource_requirement

    if resource_requirement and resource_requirement.max_replicas:
        console.print(
            f"Replicas:   {resource_requirement.min_replicas}-"
            f"{resource_requirement.max_replicas}"
        )

    autoscaler = dep_info.spec.auto_scaler

    if autoscaler:
        timeout = (
            autoscaler.scale_down.no_traffic_timeout if autoscaler.scale_down else None
        )
        if timeout:
            console.print(f"Timeout(s): {timeout}")
        target_gpu_utilization_percentage = autoscaler.target_gpu_utilization_percentage
        if target_gpu_utilization_percentage:
            console.print(f"Target GPU: {target_gpu_utilization_percentage}%")
    if workspace_id:
        web_url = LEPTON_DEPLOYMENT_URL.format(
            workspace_id=workspace_id, deployment_name=name
        )
        console.print(f"Web UI:     {web_url}/demo")
    # Note: endpoint is not quite often used right now, so we will hide it for now.
    # console.print(f"Endpoint:   {dep_info['status']['endpoint']['external_endpoint']}")
    console.print(f"Is Public:  {'No' if dep_info.spec.api_tokens else 'Yes'}")

    if show_tokens and dep_info.spec.api_tokens:

        def stringfy_token(x):
            return x.value or f"[{x.value_from.token_name_ref}]"

        console.print(f"Tokens:     {stringfy_token(dep_info.spec.api_tokens[0])}")
        for token in dep_info.spec.api_tokens[1:]:
            console.print(f"            {stringfy_token(token)}")

    console.print("Replicas List:")

    reading_issue_root = client.deployment.get_readiness(name).root
    # Print a table of readiness information.
    table = Table(show_lines=False)
    table.add_column("replica id")
    table.add_column("status")
    table.add_column("message")
    ready_count = 0
    for id, value in reading_issue_root:
        reason = value[0].reason
        message = value[0].message
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
    console.print(
        f"[green]{ready_count}[/] out of {len(reading_issue_root)} replicas ready."
    )

    deployment_terminations_root = client.deployment.get_termination(name).root

    if len(deployment_terminations_root):
        console.print("There are earlier terminations. Detailed Info:")
        table = Table(show_lines=False)
        table.add_column("replica id")
        table.add_column("start/end time")
        table.add_column("reason (code)")
        table.add_column("message")
        for id, event_list in deployment_terminations_root:
            for event in event_list:
                start_time = datetime.fromtimestamp(event.started_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                end_time = datetime.fromtimestamp(event.finished_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                code = event.exit_code
                reason = event.reason
                message = event.message if event.message else "(empty)"
                table.add_row(
                    id,
                    f"{start_time}\n{end_time}",
                    f"[yellow]{reason} ({code})[/]",
                    message,
                )
        console.print(table)


@deployment_v1.command()
@click.option("--name", "-n", help="The deployment name to get log.", required=True)
@click.option("--replica", "-r", help="The replica name to get log.", default=None)
def log(name, replica):
    """
    Gets the log of a deployment. If `replica` is not specified, the first replica
    is selected. Otherwise, the log of the specified replica is shown. To get the
    list of replicas, use `lep deployment status`.
    """
    client = APIClient()

    if not replica:
        # obtain replica information, and then select the first one.
        console.print(
            f"Replica name not specified for [yellow]{name}[/]. Selecting the first"
            " replica."
        )

        replicas = client.deployment.get_replicas()
        check(len(replicas) > 0, f"No replicas found for [red]{name}[/].")
        replica = replicas[0].metadata.id
        console.print(f"Selected replica [green]{replica}[/].")
    else:
        console.print(f"Showing log for replica [green]{replica}[/].")
    stream_or_err = client.deployment.get_log(name_or_deployment=name, replica=replica)
    # Print the log as a continuous stream until the user presses Ctrl-C.
    try:
        for chunk in stream_or_err:
            console.print(chunk, end="")
    except KeyboardInterrupt:
        console.print("Disconnected.")
    except Exception:
        console.print("Connection stopped.")
        return
    else:
        console.print(
            "End of log. It seems that the deployment has not started, or already"
            " finished."
        )
        console.print(
            f"Use `lep deployment status -n {name}` to check the status of the"
            " deployment."
        )


@deployment_v1.command()
@click.option("--name", "-n", help="The deployment name to update.", required=True)
@click.option(
    "--id",
    "-i",
    help="The new photon id to update to. Use `latest` for the latest id.",
    default=None,
)
@click.option(
    "--min-replicas",
    help=(
        "Number of replicas to update to. Pass `0` to scale the number"
        " of replicas to zero, in which case the deployemnt status page"
        " will show the deployment to be `not ready` until you scale it"
        " back with a positive number of replicas."
    ),
    type=int,
    default=None,
)
@click.option("--resource-shape", help="Resource shape.", default=None)
@click.option(
    "--public/--no-public",
    is_flag=True,
    default=None,
    help=(
        "If --public is specified, the deployment will be made public. If --no-public"
        " is specified, the deployment will be made non-public, with access tokens"
        " being the workspace token and the tokens specified by --tokens. If neither is"
        " specified, no change will be made to the access control of the deployment."
    ),
)
@click.option(
    "--tokens",
    help=(
        "Access tokens that can be used to access the deployment. See docs for"
        " details on access control. If no tokens is specified, we will not change the"
        " tokens of the deployment. If you want to remove all additional tokens, use"
        "--remove-tokens."
    ),
    multiple=True,
)
@click.option(
    "--remove-tokens",
    is_flag=True,
    default=False,
    help=(
        "If specified, all additional tokens will be removed, and the deployment will"
        " be either public (if --public) is specified, or only accessible with the"
        " workspace token (if --public is not specified)."
    ),
)
@click.option(
    "--no-traffic-timeout",
    type=int,
    default=None,
    help=(
        "If specified, the deployment will be scaled down to 0 replicas after the"
        " specified number of seconds without traffic. Set to 0 to explicitly change"
        " the deployment to have no timeout."
    ),
)
@click.option(
    "--public-photon",
    is_flag=True,
    help=(
        "If specified, get the photon from the public photon registry. If not"
        " specified, we will inherit the namespace of the current deployment."
    ),
    default=None,
)
def update(
    name,
    id,
    min_replicas,
    resource_shape,
    public,
    tokens,
    remove_tokens,
    no_traffic_timeout,
    public_photon,
):
    """
    Updates a deployment. Note that for all the update options, changes are made
    as replacements, and not incrementals. For example, if you specify `--tokens`,
    old tokens are replaced by the new set of tokens.
    """
    client = APIClient()
    if id == "latest":
        lepton_deployment = client.deployment.get(name)
        current_photon_id = lepton_deployment.spec.photon_id
        photons = client.photon.list_all()

        for photon in photons:
            if photon.id_ == current_photon_id:
                current_photon_name = photon.name
                break
        else:
            console.print(
                f"Cannot find current photon ([red]{current_photon_id}[/]) in workspace"
                f" [red]{WorkspaceInfoLocalRecord.get_current_workspace_id()}[/]."
            )
            sys.exit(1)
        records = [
            (photon.name, photon.model, photon.id_, photon.created_at)
            for photon in photons
            if photon.name == current_photon_name
        ]
        id = sorted(records, key=lambda x: x[3])[-1][2]
        console.print(f"Updating to latest photon id [green]{id}[/].")
    if public_photon is None:
        lepton_deployment = client.deployment.get(name)

        public_photon = (
            lepton_deployment.spec.photon_namespace or "private"
        ) == "public"
    if remove_tokens:
        # [] means removing all tokens
        tokens = []
    elif len(tokens) == 0:
        # None means no change
        tokens = None

    lepton_deployment_spec = LeptonDeploymentUserSpec(
        photon_namespace="public" if public_photon else "private",
        photon_id=id,
        resource_requirement=ResourceRequirement(
            min_replicas=min_replicas,
            resource_shape=resource_shape,
        ),
        api_tokens=make_token_vars_from_config(
            is_public=public,
            tokens=tokens,
        ),
        auto_scaler=(
            None
            if no_traffic_timeout is None
            else AutoScaler(scale_down=ScaleDown(no_traffic_timeout=no_traffic_timeout))
        ),
    )

    lepton_deployment = LeptonDeployment(
        metadata=Metadata(id=name), spec=lepton_deployment_spec
    )
    client.deployment.update(
        name_or_deployment=name,
        spec=lepton_deployment,
    )
    console.print(f"Deployment [green]{name}[/] updated.")


def add_command(cli_group):
    cli_group.add_command(deployment_v1)
