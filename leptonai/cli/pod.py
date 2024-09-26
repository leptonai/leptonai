"""
Pod is a module that provides a way to create and manage Lepton AI Pods.

A Pod (short for "Lepton AI Pod") is a container runtime that allows you to
run interactive sessions on the Lepton AI cloud. Think of it as a remote
server that you can access via SSH, and use it as a remote development
environment. You can use it to run Jupyter notebooks, or to run a terminal
session, similar to a cloud VM but much more lightweight.
"""

import subprocess
import sys
import json
from datetime import datetime
import re
import shlex

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from leptonai.config import (
    VALID_SHAPES,
    DEFAULT_RESOURCE_SHAPE,
    SSH_PORT,
    TCP_PORT,
    TCP_JUPYTER_PORT,
)
from leptonai.api.v1 import types
from .util import (
    click_group,
    _get_only_replica_public_ip,
    _get_valid_nodegroup_ids,
    _get_valid_node_ids,
)
from ..api.v1.client import APIClient
from ..api.v1.photon import make_mounts_from_strings, make_env_vars_from_strings
from ..api.v1.types.affinity import LeptonResourceAffinity
from ..api.v1.types.deployment import ResourceRequirement, LeptonLog, LeptonContainer


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
@click.option("--container-image", type=str, help="Container image to run.")
@click.option(
    "--container-command",
    type=str,
    help="Command to run in the container.",
)
@click.option(
    "--log-collection",
    "-lg",
    type=bool,
    help=(
        "Enable or disable log collection (true/false). If not provided, the workspace"
        " setting will be used."
    ),
)
@click.option(
    "--node-id",
    "-ni",
    "node_ids",
    help=(
        "Node for the pod. You can repeat this flag multiple times to choose multiple"
        " nodes. Please specify the node group when you are using this option"
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
    container_image,
    container_command,
    log_collection,
    node_ids,
):
    """
    Creates a pod with the given resource shape, mount, env and secret.
    """

    if resource_shape is None:
        available_types = "\n      ".join(VALID_SHAPES)
        console.print(
            "[red]Error: Missing option '--resource-shape'.[/] "
            f"Available types are:\n      {available_types}. \n"
        )
        sys.exit(1)

    spec_container = None
    if container_image or container_command:
        if container_image is None:
            console.print(
                "Error: container image and command must be specified together."
            )
            sys.exit(1)

        spec_container = LeptonContainer(
            image=container_image,
            command=shlex.split(container_command) if container_command else None,
        )

    client = APIClient()

    resource_requirement = ResourceRequirement(
        resource_shape=resource_shape or DEFAULT_RESOURCE_SHAPE,
    )

    if node_groups:
        node_group_ids = _get_valid_nodegroup_ids(node_groups)
        valid_node_ids = _get_valid_node_ids(node_group_ids, node_ids)
        # make sure affinity is initialized
        resource_requirement.affinity = LeptonResourceAffinity(
            allowed_dedicated_node_groups=node_group_ids,
            allowed_nodes_in_node_group=valid_node_ids,
        )

    try:
        deployment_user_spec = types.deployment.LeptonDeploymentUserSpec(
            container=spec_container,
            resource_requirement=resource_requirement,
            mounts=make_mounts_from_strings(mount),
            image_pull_secrets=image_pull_secrets,
            envs=make_env_vars_from_strings(list(env), list(secret)),
            is_pod=True,
        )
        if log_collection is not None:
            deployment_user_spec.log = LeptonLog(enable_collection=log_collection)

        deployment_spec = types.deployment.LeptonDeployment(
            metadata=types.common.Metadata(name=name),
            spec=deployment_user_spec,
        )

    except ValueError as e:
        console.print(f"Error encountered while processing pod configs:\n[red]{e}[/].")
        console.print("Failed to create pod.")
        sys.exit(1)

    logger.trace(json.dumps(deployment_spec.model_dump(), indent=2))
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

    pods_count = len(pods)
    ssh_ports = [None] * pods_count
    tcp_ports = [None] * pods_count
    tcp_ports_jupyterlab = [None] * pods_count
    for index, pod in enumerate(pods):
        ports = pod.spec.container.ports
        port_pairs = [(p.container_port, p.host_port) for p in ports]
        if len(port_pairs) not in [2, 3]:
            console.print(
                f"Pod {pod.metadata.name} does not have exactly two or three ports."
                f" This is not supported. it has \n {port_pairs}"
            )
            continue

        for port_pair in port_pairs:
            if port_pair[0] == SSH_PORT:
                ssh_ports[index] = port_pair
            elif port_pair[0] == TCP_PORT:
                tcp_ports[index] = port_pair
            elif len(port_pairs) == 3 and port_pair[0] == TCP_JUPYTER_PORT:
                tcp_ports_jupyterlab[index] = port_pair
            else:
                console.print(
                    f"Warning: Pod [red]{pod.metadata.name}[/] has an unsupported port"
                    f" [red]{port_pair}.[/]"
                )

    pod_ips = [None] * pods_count
    for index, pod in enumerate(pods):
        if pod.status.state in ("Running", "Ready"):
            public_ip = _get_only_replica_public_ip(pod.metadata.name)
            pod_ips[index] = public_ip
    logger.trace(f"Pod IPs:\n{pod_ips}")

    table = Table(title="pods", show_lines=True)
    table.add_column("name")
    table.add_column("resource shape")
    table.add_column("status")
    table.add_column("ssh command")
    table.add_column("TCP port mapping")
    table.add_column(
        "TCP port mapping \n (Jupyterlab)",
        justify="center",
    )
    table.add_column("created at")
    for pod, ssh_port, tcp_port, tcp_port_jupyterlab, pod_ip in zip(
        pods, ssh_ports, tcp_ports, tcp_ports_jupyterlab, pod_ips
    ):
        Jupyter_lab_mapping = (
            f"{tcp_port_jupyterlab[0]} -> {tcp_port_jupyterlab[1]} \n(pod  -> client)"
            if tcp_port_jupyterlab
            else "Not Available"
        )
        table.add_row(
            pod.metadata.name,
            pod.spec.resource_requirement.resource_shape,
            pod.status.state,
            (
                f"ssh -p {ssh_port[1]} root@{pod_ip}"
                if (pod_ip and ssh_port)
                else "Not Available"
            ),
            (
                f"{tcp_port[0]} -> {tcp_port[1]} \n(pod  -> client)"
                if tcp_port
                else "Not Available"
            ),
            Jupyter_lab_mapping,
            datetime.fromtimestamp(pod.metadata.created_at / 1000).strftime(
                "%Y-%m-%d\n%H:%M:%S"
            ),
        )
    console.print(table)
    console.print(
        "* TCP port mapping(JupyterLab) defaults to the port that JupyterLab"
        " listens on."
    )
    console.print(
        "* Your initial ssh password is the workspace token.\n* Use `lep workspace"
        " token` to get the token if needed."
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


@pod.command()
@click.option("--name", "-n", help="The pod name to ssh.", required=True)
def ssh(name):
    client = APIClient()

    pod = client.deployment.get(name)
    ports = pod.spec.container.ports
    if pod.status.state not in ("Running", "Ready"):
        console.print("This pod is not running or is not ready.")
        sys.exit(1)

    public_ip = _get_only_replica_public_ip(pod.metadata.name)

    if not public_ip:
        console.print(
            "No public IP is found, you can choose to use the web terminal to access"
            " the pod."
            f"https://dashboard.lepton.ai/workspace/stable/compute/pods/detail/{name}/terminal"
        )
        sys.exit(0)

    ssh_flag = False
    for port in ports:
        if port.container_port == SSH_PORT:
            ssh_flag = True
            try:
                logger.trace(f"ssh -p {port.host_port} root@{public_ip}")
                subprocess.run(
                    ["ssh", "-p", str(port.host_port), f"root@{str(public_ip)}"],
                    check=True,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as e:
                if e.returncode == 130:
                    console.print("[green] SSH session exited normally.[/]")
                else:
                    console.print(
                        f"[red]SSH command failed with exit statu[/] {e.returncode}"
                    )
                    console.print(
                        "[red]Error output:"
                        f" {e.stderr if e.stderr else 'No error output captured.'}[/]"
                    )
            except Exception as e:
                console.print(f"[red]An unexpected error occurred: {str(e)}[/]")

    if not ssh_flag:
        console.print(
            "SSH port not found, you can choose to use the web terminal to access the"
            " pod."
            f"https://dashboard.lepton.ai/workspace/stable/compute/pods/detail/{name}/terminal"
        )
        sys.exit(1)


def add_command(cli_group):
    cli_group.add_command(pod)
