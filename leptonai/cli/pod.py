"""
Pod is a module that provides a way to create and manage Lepton AI Pods.

A Pod (short for "Lepton AI Pod") is a container runtime that allows you to
run interactive sessions on the Lepton AI cloud. Think of it as a remote
server that you can access via SSH, and use it as a remote development
environment. You can use it to run Jupyter notebooks, or to run a terminal
session, similar to a cloud VM but much more lightweight.
"""

from datetime import datetime
import re
import sys

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from leptonai.config import VALID_SHAPES
from leptonai.api.v1 import types
from .util import (
    click_group,
    check,
    _get_only_replica_public_ip,
    _get_valid_nodegroup_ids,
)
from ..api.v1.client import APIClient
from ..api.v1.photon import make_mounts_from_strings, make_env_vars_from_strings
from ..api.v1.types.affinity import LeptonResourceAffinity
from ..api.v1.types.deployment import ResourceRequirement

console = Console(highlight=False)


@click_group()
def pod():
    """
    Manages pods on the Lepton AI cloud.

    A Pod (short for "Lepton AI Pod") is a container runtime that allows you to
    run interactive sessions on the Lepton AI cloud. Think of it as a remote
    server that you can access via SSH, and use it as a remote development
    environment. You can use it to run Jupyter notebooks, or to run a terminal
    session, similar to a cloud VM but much more lightweight.
    """
    pass


@pod.command()
@click.option("--name", "-n", type=str, help="Name of the pod to create.")
@click.option(
    "--resource-shape",
    type=str,
    help="Resource shape for the pod. Available types are: '"
    + "', '".join(VALID_SHAPES)
    + "'.",
    default=None,
)
@click.option(
    "--mount",
    help=(
        "Persistent storage to be mounted to the deployment, in the format"
        " `STORAGE_PATH:MOUNT_PATH`."
    ),
    multiple=True,
)
@click.option(
    "--env",
    "-e",
    help="Environment variables to pass to the deployment, in the format `NAME=VALUE`.",
    multiple=True,
)
@click.option(
    "--secret",
    "-s",
    help=(
        "Secrets to pass to the deployment, in the format `NAME=SECRET_NAME`. If"
        " secret name is also the environment variable name, you can"
        " omit it and simply pass `SECRET_NAME`."
    ),
    multiple=True,
)
@click.option(
    "--image-pull-secrets",
    type=str,
    help="Secrets to use for pulling images.",
    multiple=True,
)
@click.option(
    "--node-group",
    "-ng",
    "node_groups",
    help=(
        "Node group for the pod. If not set, use on-demand resources. You can repeat"
        " this flag multiple times to choose multiple node groups. Multiple node group"
        " option is currently not supported but coming soon for enterprise users. Only"
        " the first node group will be set if you input multiple node groups at this"
        " time."
    ),
    type=str,
    multiple=True,
)
def create(
    name,
    resource_shape,
    mount,
    env,
    secret,
    image_pull_secrets,
    node_groups,
):
    """
    Creates a pod with the given resource shape, mount, env and secret.
    """
    client = APIClient()

    resource_requirement = ResourceRequirement(
        resource_shape=resource_shape,
    )

    if node_groups:
        node_group_ids = _get_valid_nodegroup_ids(node_groups)
        # make sure affinity is initialized
        resource_requirement.affinity = LeptonResourceAffinity(
            allowed_dedicated_node_groups=node_group_ids,
        )

    try:
        deployment_user_spec = types.deployment.LeptonDeploymentUserSpec(
            resource_requirement=resource_requirement,
            mounts=make_mounts_from_strings(mount),
            image_pull_secrets=image_pull_secrets,
            envs=make_env_vars_from_strings(list(env), list(secret)),
            is_pod=True,
        )
        deployment_spec = types.deployment.LeptonDeployment(
            metadata=types.common.Metadata(name=name),
            spec=deployment_user_spec,
        )
    except ValueError as e:
        console.print(f"Error encountered while processing pod configs:\n[red]{e}[/].")
        console.print("Failed to create pod.")
        sys.exit(1)

    client.photon.run(deployment_spec)

    console.print(f"Pod launched as [green]{name}[/]")


@pod.command(name="list")
@click.option(
    "--pattern",
    "-p",
    help="Regular expression pattern to filter pod names.",
    default=None,
)
def list_command(pattern):
    """
    Lists all pods in the current workspace.
    """
    client = APIClient()

    deployments = client.deployment.list_all()

    logger.trace(f"Deployments:\n{[d for d in deployments if d.spec.is_pod]}")
    pods = [
        d
        for d in deployments
        if d.spec.is_pod and (pattern is None or re.search(pattern, d.metadata.name))
    ]
    if len(pods) == 0:
        console.print("No pods found. Use `lep pod create` to create pods.")
        return 0
    ssh_ports = []
    tcp_ports = []
    for pod in pods:
        ports = pod.spec.container.ports
        port_pairs = [(p.container_port, p.host_port) for p in ports]
        check(
            len(port_pairs) == 2,
            f"Pod {pod.metadata.name} does not have exactly two ports. This is not"
            " supported.",
        )
        if port_pairs[0][0] == 2222:
            ssh_ports.append(port_pairs[0])
            tcp_ports.append(port_pairs[1])
        else:
            ssh_ports.append(port_pairs[1])
            tcp_ports.append(port_pairs[0])
    pod_ips = []
    for pod in pods:
        if pod.status.state not in ("Running", "Ready"):
            pod_ips.append(None)
            continue
        public_ip = _get_only_replica_public_ip(pod.metadata.name)
        pod_ips.append(public_ip)
    logger.trace(f"Pod IPs:\n{pod_ips}")

    table = Table(title="pods", show_lines=True)
    table.add_column("name")
    table.add_column("resource shape")
    table.add_column("status")
    table.add_column("ssh command")
    table.add_column("TCP port mapping")
    table.add_column("created at")
    for pod, ssh_port, tcp_port, pod_ip in zip(pods, ssh_ports, tcp_ports, pod_ips):
        table.add_row(
            pod.metadata.name,
            pod.spec.resource_requirement.resource_shape,
            pod.status.state,
            f"ssh -p {ssh_port[1]} root@{pod_ip}" if pod_ip is not None else "N/A",
            f"{tcp_port[0]} -> {tcp_port[1]} \n(pod  -> client)",
            datetime.fromtimestamp(pod.metadata.created_at / 1000).strftime(
                "%Y-%m-%d\n%H:%M:%S"
            ),
        )
    console.print(table)
    console.print(
        "Your initial ssh password is the workspace token.\nUse `lep workspace token`"
        " to get the token if needed."
    )
    return 0


@pod.command()
@click.option("--name", "-n", help="The pod name to remove.", required=True)
def remove(name):
    """
    Removes a pod.
    """

    client = APIClient()

    client.deployment.delete(name)
    console.log(f"Pod [green]{name}[/] removed.")

    return 0


def add_command(cli_group):
    cli_group.add_command(pod)
