from datetime import datetime
import re
import shlex
import sys
from typing import List, Optional, Union

import click
from loguru import logger
from rich.table import Table

from .util import (
    console,
    check,
    click_group,
    _get_valid_nodegroup_ids,
)

from leptonai.config import (
    VALID_SHAPES,
    LEPTON_DEPLOYMENT_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_RESOURCE_SHAPE,
    ENV_VAR_REQUIRED,
)
from ..api.v1.client import APIClient
from ..api.v1.deployment import make_token_vars_from_config
from ..api.v1.photon import make_mounts_from_strings, make_env_vars_from_strings
from ..api.v1.types.affinity import LeptonResourceAffinity
from ..api.v1.workspace_record import WorkspaceRecord
from ..api.v1.types.common import Metadata, LeptonVisibility
from ..api.v1.types.deployment import (
    AutoScaler,
    HealthCheck,
    HealthCheckLiveness,
    LeptonDeployment,
    LeptonDeploymentUserSpec,
    LeptonContainer,
    ResourceRequirement,
    ScaleDown,
    ContainerPort,
    AutoscalerTargetThroughput,
)
from ..api.v1.types.photon import PhotonDeploymentTemplate


def autoscale_flag_deprecation_warning(ctx, param, value):
    if value is not None:
        click.echo(
            f"""Warning: The '{param.name}' option will be deprecated in a future release. 
        Please consider using the new options for replica number and autoscale policy management: 
        '-r'
        '--replicas-static <replica_number>' 
        
        '-ad'  
        '--autoscale-down <replica_number>,<timeout>' 
         
        '-agu'
        '--autoscale-gpu-util <min_replica>,<max_replica>,<gpu-util-threshold>' 
        
        '-aq'
        '--autoscale-qpm <min_replica>,<max_replica>,<qpm-threshold>'
        
        please use lep deployment create -h for more information.
        """,
            err=True,
        )
    return value


def validate_autoscale_options(ctx, param, value):
    replicas_static = ctx.params.get("replicas_static")
    autoscale_down = ctx.params.get("autoscale_down")
    autoscale_gpu_util = ctx.params.get("autoscale_gpu_util")
    autoscale_qpm = ctx.params.get("autoscale_qpm")
    no_traffic_timeout = ctx.params.get("no_traffic_timeout")
    target_gpu_utilization = ctx.params.get("target_gpu_utilization")
    max_replicas = ctx.params.get("max_replicas")
    min_replicas = ctx.params.get("min_replicas")

    num_new_options = sum(
        option is not None
        for option in [
            replicas_static,
            autoscale_down,
            autoscale_gpu_util,
            autoscale_qpm,
        ]
    )
    if num_new_options > 1:
        raise click.UsageError(
            "You cannot use --replicas-static, --autoscale-down, --autoscale-gpu-util,"
            " and autoscale-qpm options together. Please specify only one."
        )

    num_old_options = sum(
        option is not None
        for option in [
            no_traffic_timeout,
            target_gpu_utilization,
            max_replicas,
        ]
    )

    if num_new_options > 0 and (
        num_old_options >= 1 or (min_replicas is not None and min_replicas > 1)
    ):
        raise click.UsageError(
            """You cannot use deprecating autoscale options with new autoscale options.
            Please specify only one of the following:
            
            '-r'
            '--replicas-static <replica_number>' 
            
            '-ad'  
            '--autoscale-down <replica_number>,<timeout>' 
             
            '-agu'
            '--autoscale-gpu-util <min_replica>,<max_replica>,<gpu-util-threshold>' 
            
            '-aq'
            '--autoscale-qpm <min_replica>,<max_replica>,<qpm-threshold>'
            """
        )

    if param.name == "autoscale_down" and value:
        parts = value.split(",")
        if (
            len(parts) != 2
            or not parts[0].isdigit()
            or not (parts[1].endswith("s") or parts[1].isdigit())
        ):
            raise click.BadParameter(
                "Invalid format for --autoscale-down. Expected format:"
                " <replicas>,<timeout>s or <replicas>,<timeout>"
            )
        try:
            replicas = int(parts[0])
            timeout = int(parts[1].rstrip("s"))
            if replicas < 0 or timeout < 0:
                raise ValueError
        except ValueError:
            raise click.BadParameter(
                "Replicas and timeout should be positive integers."
            )

    if param.name == "autoscale_gpu_util" and value:
        parts = value.split(",")
        if len(parts) != 3 or not (
            parts[0].isdigit()
            and parts[1].isdigit()
            and (parts[2].rstrip("%").isdigit())
        ):
            raise click.BadParameter(
                "Invalid format for --autoscale-between. Expected format:"
                " <min_replica>,<max_replica>,<threshold>% or"
                " <min_replica>,<max_replica>,<threshold>"
            )
        try:
            min_replica = int(parts[0])
            max_replica = int(parts[1])
            threshold = int(parts[2].rstrip("%"))
            if min_replica < 0 or max_replica < 0 or not (0 <= threshold <= 99):
                raise ValueError
        except ValueError:
            raise click.BadParameter(
                "Min_replica, max_replica should be positive integers and threshold"
                " should be between 0 and 99."
            )

    if param.name == "autoscale_qpm" and value:
        parts = value.split(",")
        if len(parts) != 3 or not (
            parts[0].isdigit() and parts[1].isdigit() and is_positive_number(parts[2])
        ):
            raise click.BadParameter(
                "Invalid format for --autoscale-qpm. Expected format:"
                " <min_replica>,<max_replica>,<threshold>"
            )
        try:
            min_replica = int(parts[0])
            max_replica = int(parts[1])
            threshold = float(parts[2])
            if min_replica < 0 or max_replica < 0 or threshold < 0:
                raise ValueError
        except ValueError:
            raise click.BadParameter(
                "Min_replica and max_replica should be positive integers and threshold"
                " should be a positive number."
            )

    return value


def is_positive_number(value):
    try:
        num = float(value)
        return num > 0
    except ValueError:
        return False


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


def _timeout_must_be_larger_than_60(unused_ctx, unused_param, x):
    if x is not None:
        autoscale_flag_deprecation_warning(unused_ctx, unused_param, x)
    if x is None or x == 0 or x >= 60:
        return x
    else:
        raise click.BadParameter("Timeout value must be larger than 60 seconds.")


def _get_ordered_photon_ids_or_none(
    name: str, public_photon: bool
) -> Union[List[str], None]:
    """Returns a list of photon ids for a given name, in the order newest to
    oldest. If no photon of such name exists, returns None.
    """

    client = APIClient()

    photons = client.photon.list_all(public_photon=public_photon)

    target_photons = [p for p in photons if p.name == name]  # type: ignore
    if len(target_photons) == 0:
        return None
    target_photons.sort(key=lambda p: p.created_at, reverse=True)  # type: ignore
    return [p.id_ for p in target_photons]  # type: ignore


def _get_most_recent_photon_id_or_none(name: str, public_photon: bool) -> Optional[str]:
    """Returns the most recent photon id for a given name. If no photon of such
    name exists, returns None.
    """
    photon_ids = _get_ordered_photon_ids_or_none(name, public_photon)
    return photon_ids[0] if photon_ids else None


def _create_workspace_token_secret_var_if_not_existing(client: APIClient):
    """
    Adds the workspace token as a secret environment variable.
    """
    from ..api.v1.types.common import SecretItem

    secrets = client.secret.list_all()
    if "LEPTON_WORKSPACE_TOKEN" not in secrets:
        current_ws = WorkspaceRecord.current()
        if current_ws is None:
            console.print(
                "Error: you are not logged in yet. Log into your workspace before"
                " using --include-workspace-token."
            )
            sys.exit(1)
        else:
            token = current_ws.auth_token
            # TODO: there woudln't be a case when token is empty, but we will add a check
            # here just in case.
            if token:
                client.secret.create(
                    [SecretItem(name="LEPTON_WORKSPACE_TOKEN", value=token)]
                )


@deployment.command()
@click.option("--name", "-n", type=str, help="Name of the deployment being created.")
@click.option(
    "--photon", "-p", "photon_name", type=str, help="Name of the photon to run."
)
@click.option(
    "--photon-id",
    "-i",
    type=str,
    help=(
        "Specific version id of the photon to run. If not specified, we will run the"
        " most recent version of the photon."
    ),
)
@click.option("--container-image", type=str, help="Container image to run.")
@click.option(
    "--container-port",
    type=int,
    help=(
        "Guest OS port to listen to in the container. If not specified, default to"
        " 8080."
    ),
)
@click.option(
    "--container-command",
    type=str,
    help=(
        "Command to run in the container. Your command should listen to the port"
        " specified by --container-port."
    ),
)
@click.option(
    "--resource-shape",
    type=str,
    help="Resource shape for the deployment. Available types are: '"
    + "', '".join(VALID_SHAPES)
    + "'.",
    default=None,
)
@click.option(
    "--min-replicas",
    type=int,
    help="(Will be deprecated soon) Minimum number of replicas.",
    default=1,
)
@click.option(
    "--max-replicas",
    type=int,
    help="(Will be deprecated) Maximum number of replicas.",
    default=None,
    callback=autoscale_flag_deprecation_warning,
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
    "--public",
    is_flag=True,
    help=(
        "If specified, the photon will be publicly accessible. See docs for details "
        "on access control."
    ),
)
@click.option(
    "--tokens",
    help=(
        "Additional tokens that can be used to access the photon. See docs for details "
        "on access control."
    ),
    multiple=True,
)
@click.option(
    "--no-traffic-timeout",
    type=int,
    help=(
        "(Will be deprecated soon)"
        "If specified, the deployment will be scaled down to 0 replicas after the"
        " specified number of seconds without traffic. Minimum is 60 seconds if set."
        " Note that actual timeout may be up to 30 seconds longer than the specified"
        " value."
    ),
    callback=_timeout_must_be_larger_than_60,
)
@click.option(
    "--target-gpu-utilization",
    type=int,
    help=(
        "(Will be deprecated soon)"
        "If min and max replicas are set, if the gpu utilization is higher than the"
        " target gpu utilization, autoscaler will scale up the replicas. If the gpu"
        " utilization is lower than the target gpu utilization, autoscaler will scale"
        " down the replicas. The value should be between 0 and 99."
    ),
    default=None,
    callback=autoscale_flag_deprecation_warning,
)
@click.option(
    "--initial-delay-seconds",
    type=int,
    help=(
        "If specified, the deployment will allow the specified amount of seconds for"
        " the photon to initialize before it starts the service. Usually you should"
        " not need this. If you have a deployment that takes a long time to initialize,"
        " set it to a longer value."
    ),
    default=None,
)
@click.option(
    "--include-workspace-token",
    is_flag=True,
    help=(
        "If specified, the workspace token will be included as an environment"
        " variable. This is used when the photon code uses Lepton SDK capabilities such"
        " as queue, KV, objectstore etc. Note that you should trust the code in the"
        " photon, as it will have access to the workspace token."
    ),
    default=False,
)
@click.option(
    "--rerun",
    is_flag=True,
    help=(
        "If specified, shutdown the deployment of the same deployment name and"
        " rerun it. Note that this may cause downtime of the photon if it is for"
        " production use, so use with caution. In a production environment, you"
        " should do photon create, push, and `lep deployment update` instead."
    ),
    default=False,
)
@click.option(
    "--public-photon",
    is_flag=True,
    help=(
        "If specified, get the photon from the public photon registry. This is only"
        " supported for remote execution."
    ),
    default=False,
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
        "Node group for the deployment. If not set, use on-demand resources. You can"
        " repeat this flag multiple times to choose multiple node groups. Multiple node"
        " group option is currently not supported but coming soon for enterprise users."
        " Only the first node group will be set if you input multiple node groups at"
        " this time."
    ),
    type=str,
    multiple=True,
)
@click.option(
    "--visibility",
    type=str,
    help=(
        "Visibility of the deployment. Can be 'public' or 'private'. If private, the"
        " deployment will only be viewable by the creator and workspace admin."
    ),
)
@click.option(
    "--replicas-static",
    "-r",
    "-replicas",
    type=int,
    default=None,
    help="""
                Use this option if you want a fixed number of replicas and want to turn off autoscaling.
                For example, to set a fixed number of replicas to 2, you can use: 
                --replicas-static 2  or
                -r 2
            """,
    callback=validate_autoscale_options,
)
@click.option(
    "--autoscale-down",
    "-ad",
    type=str,
    default=None,
    help="""
                Use this option if you want to have replicas but scale down after a specified time of no traffic.
                For example, to set 2 replicas and scale down after 3600 seconds of no traffic,
                use: --autoscale-down 2,3600s or --autoscale-down 2,3600
                (Note: Do not include spaces around the comma.)
            """,
    callback=validate_autoscale_options,
)
@click.option(
    "--autoscale-gpu-util",
    "-agu",
    type=str,
    default=None,
    help="""
                Use this option to set a threshold for GPU utilization and enable the system to scale between
                a minimum and maximum number of replicas. For example,
                to scale between 1 (min_replica) and 3 (max_replica) with a 50% threshold,
                use: --autoscale-between 1,3,50% or --autoscale-between 1,3,50
                (Note: Do not include spaces around the comma.)

                If the GPU utilization is higher than the target GPU utilization,
                the autoscaler will scale up the replicas.
                If the GPU utilization is lower than the target GPU utilization,
                the autoscaler will scale down the replicas.
                The threshold value should be between 0 and 99.
                
            """,
    callback=validate_autoscale_options,
)
@click.option(
    "--autoscale-qpm",
    "-aq",
    type=str,
    default=None,
    help="""
                Use this option to set a threshold for QPM and enable the system to scale between
                a minimum and maximum number of replicas. For example,
                to scale between 1 (min_replica) and 3 (max_replica) with a 2.5 QPM,
                use: --autoscale-between 1,3,2.5
                (Note: Do not include spaces around the comma.)

                If the QPM is higher than the target QPM,
                the autoscaler will scale up the replicas.
                If the QPM is lower than the target QPM,
                the autoscaler will scale down the replicas.
                The threshold value should be between positive number.
            """,
    callback=validate_autoscale_options,
)
def create(
    name,
    photon_name,
    photon_id,
    container_image,
    container_port,
    container_command,
    resource_shape,
    min_replicas,
    max_replicas,
    mount,
    env,
    secret,
    public,
    tokens,
    no_traffic_timeout,
    target_gpu_utilization,
    initial_delay_seconds,
    include_workspace_token,
    rerun,
    public_photon,
    image_pull_secrets,
    node_groups,
    visibility,
    replicas_static,
    autoscale_down,
    autoscale_gpu_util,
    autoscale_qpm,
):
    """
    Creates a deployment from either a photon or container image.
    """
    client = APIClient()
    spec = LeptonDeploymentUserSpec()

    existing_deployments = client.deployment.list_all()
    if name in [d.metadata.name for d in existing_deployments]:
        if rerun:
            console.print(
                f"Deployment [green]{name}[/] already exists. Shutting down the"
                " existing deployment and rerunning."
            )
            client.deployment.delete(name)
        else:
            console.print(
                f"Deployment [green]{name}[/] already exists. Use `lep deployment"
                f" update -n {name}` to update the deployment, or add `--rerun` to"
                " shutdown the existing deployment and rerun it."
            )
            sys.exit(1)

    # First, check whether the input is photon or container. We will prioritize using
    # photon if both are specified.
    if photon_name is not None or photon_id is not None:
        # We will use photon.
        if container_image is not None or container_command is not None:
            console.print(
                "Warning: both photon and container image are specified. We will use"
                " the photon."
            )
        if photon_id is None:
            # look for the latest photon with the given name.
            photon_id = _get_most_recent_photon_id_or_none(photon_name, public_photon)
            if not photon_id:
                console.print(
                    f"Photon [red]{name}[/] does not exist in the workspace. Did"
                    " you forget to push the photon?",
                )
                sys.exit(1)
            console.print(
                f"Running the most recent version of [green]{name}[/]: {photon_id}"
            )
        else:
            console.print(f"Running the specified version: [green]{photon_id}[/]")
        spec.photon_id = photon_id
        spec.photon_namespace = "public" if public_photon else "private"

        # get deployment template
        photon = client.photon.get(photon_id, public_photon=public_photon)  # type: ignore
        deployment_template = photon.deployment_template
    elif container_image is not None or container_command is not None:
        # We will use container.
        if container_image is None or container_command is None:
            console.print(
                "Error: container image and command must be specified together."
            )
            sys.exit(1)
        spec.container = LeptonContainer(
            image=container_image,
            command=shlex.split(container_command),
        )
        if container_port:
            spec.container.ports = [ContainerPort(container_port=container_port)]
        # container based deployment won't have the deployment template as photons do.
        # So we will simply create an empty one.
        deployment_template = PhotonDeploymentTemplate()
    else:
        # No photon_id, photon_name, container_image, or container_command
        console.print("""
            You have not provided a photon_name, photon_id, or container image.
            Please use one of the following options:
            -p <photon_name>
            -i <photon_id>
            --container-image <container_image> and --container-command <container_command>
            to specify a photon or container image.
            """)
        sys.exit(1)
    # default timeout
    if (
        no_traffic_timeout is None
        and DEFAULT_TIMEOUT
        and target_gpu_utilization is None
        and replicas_static is None
        and autoscale_down is None
        and autoscale_gpu_util is None
        and autoscale_qpm is None
    ):
        console.print(
            "\nLepton is currently set to use a default timeout of [green]1"
            " hour[/]. This means that when there is no traffic for more than an"
            " hour, your deployment will automatically scale down to zero. This is"
            " to assist auto-release of unused debug deployments.\n- If you would"
            " like to run a long-running photon (e.g. for production), [green]set"
            " --no-traffic-timeout to 0[/].\n- If you would like to turn off"
            " default timeout, set the environment variable"
            " [green]LEPTON_DEFAULT_TIMEOUT=false[/].\n"
        )
        no_traffic_timeout = DEFAULT_TIMEOUT

    threshold = None

    if replicas_static:
        min_replicas = replicas_static
        max_replicas = replicas_static
        no_traffic_timeout = None

    if autoscale_down:
        parts = autoscale_down.split(",")
        replicas = int(parts[0])
        timeout = int(parts[1].rstrip("s"))
        min_replicas = replicas
        max_replicas = replicas
        no_traffic_timeout = timeout

    if autoscale_gpu_util:
        parts = autoscale_gpu_util.split(",")
        min_replicas = int(parts[0])
        max_replicas = int(parts[1])
        target_gpu_utilization = int(parts[2].rstrip("%"))

    if autoscale_qpm:
        parts = autoscale_qpm.split(",")
        min_replicas = int(parts[0])
        max_replicas = int(parts[1])
        threshold = float(parts[2])

    # resources
    spec.resource_requirement = ResourceRequirement(
        resource_shape=resource_shape
        or (deployment_template.resource_shape if deployment_template else None)
        or DEFAULT_RESOURCE_SHAPE,
        min_replicas=min_replicas,
        max_replicas=max_replicas,
    )

    if node_groups:
        node_group_ids = _get_valid_nodegroup_ids(node_groups)
        spec.resource_requirement.affinity = LeptonResourceAffinity(
            allowed_dedicated_node_groups=node_group_ids,
        )

    # include workspace token
    secret = list(secret)  # to convert secret from tuple to list
    if include_workspace_token:
        console.print("Including the workspace token for the photon execution.")
        _create_workspace_token_secret_var_if_not_existing(client)
        if "LEPTON_WORKSPACE_TOKEN" not in secret:
            secret += [
                "LEPTON_WORKSPACE_TOKEN",
            ]

    try:
        logger.trace(f"deployment_template:\n{deployment_template}")
        template_envs = deployment_template.env or {}
        env_list = env or []
        secret_list = secret or []
        mount_list = mount or []
        for k, v in template_envs.items():
            if v == ENV_VAR_REQUIRED:
                if not any(s.startswith(k + "=") for s in (env or [])):
                    console.print(
                        f"This deployment requires env var {k}, but it's missing."
                        f" Please specify it with --env {k}=YOUR_VALUE. Otherwise,"
                        " the deployment may fail."
                    )
            else:
                if not any(s.startswith(k + "=") for s in env_list):
                    # Adding default env variable if not specified.
                    env_list.append(f"{k}={v}")
        template_secrets = deployment_template.secret or []
        for k in template_secrets:
            if k not in secret_list:
                console.print(
                    f"This deployment requires secret {k}, but it's missing. Please"
                    f" set the secret, and specify it with --secret {k}. Otherwise,"
                    " the deployment may fail."
                )
        spec.envs = make_env_vars_from_strings(env_list, secret_list)
        spec.mounts = make_mounts_from_strings(mount_list)
        spec.api_tokens = make_token_vars_from_config(public, tokens)
        spec.image_pull_secrets = list(image_pull_secrets)
        spec.auto_scaler = AutoScaler(
            scale_down=(
                ScaleDown(no_traffic_timeout=no_traffic_timeout)
                if no_traffic_timeout
                else None
            ),
            target_gpu_utilization_percentage=target_gpu_utilization,
            target_throughput=(
                AutoscalerTargetThroughput(qpm=threshold) if threshold else None
            ),
        )

        spec.health = HealthCheck(
            liveness=(
                HealthCheckLiveness(initial_delay_seconds=initial_delay_seconds)
                if initial_delay_seconds
                else None
            )
        )
    except ValueError as e:
        console.print(
            f"Error encountered while processing deployment configs:\n[red]{e}[/]."
        )
        console.print("Failed to launch deployment.")
        sys.exit(1)
    name = name if name else (photon_name or photon_id)
    lepton_deployment = LeptonDeployment(
        metadata=Metadata(
            id=name,
            name=name,
            visibility=LeptonVisibility(visibility) if visibility else None,
        ),
        spec=spec,
    )
    client.deployment.create(lepton_deployment)
    console.print(
        f"Deployment created as [green]{name}[/]. Use `lep deployment"
        f" status -n {name}` to check the status."
    )


@deployment.command(name="list")
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
            d.metadata.created_at
            / 1000,  # convert to seconds from milliseconds # type: ignore
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
        if pattern is not None and (name is None or not re.search(pattern, name)):
            continue
        table.add_row(
            name,
            photon_id,
            datetime.fromtimestamp(created_at).strftime("%Y-%m-%d\n%H:%M:%S"),
            status.state,
        )
    console.print(table)
    return 0


@deployment.command()
@click.option("--name", "-n", help="The deployment name to remove.", required=True)
def remove(name):
    """
    Removes a deployment.
    """
    client = APIClient()
    client.deployment.delete(name)
    console.print(f"Job [green]{name}[/] deleted successfully.")


@deployment.command()
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
    workspace_id = client.get_workspace_id()

    # todo: print a cleaner dep info.
    creation_time = datetime.fromtimestamp(
        dep_info.metadata.created_at / 1000  # type: ignore
    ).strftime("%Y-%m-%d %H:%M:%S")

    state = dep_info.status.state
    if state in ("Running", "Ready"):
        state = f"[green]{state}[/]"
    else:
        state = f"[yellow]{state}[/]"
    console.print(f"Time now:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(f"Created at: {creation_time}")

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
    for id, value in reading_issue_root.items():
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
        for id, event_list in deployment_terminations_root.items():
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


@deployment.command()
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

        replicas = client.deployment.get_replicas(name)
        check(len(replicas) > 0, f"No replicas found for [red]{name}[/].")
        replica = replicas[0].metadata.id_
        console.print(f"Selected replica [green]{replica}[/].")
    else:
        console.print(f"Showing log for replica [green]{replica}[/].")
    stream_or_err = client.deployment.get_log(name_or_deployment=name, replica=replica)  # type: ignore
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


@deployment.command()
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
@click.option(
    "--visibility",
    type=str,
    help=(
        "Visibility of the deployment. Can be 'public' or 'private'. If private, the"
        " deployment will only be viewable by the creator and workspace admin."
    ),
)
@click.option(
    "--replicas-static",
    "-r",
    "-replicas",
    type=int,
    default=None,
    help="""
                Use this option if you want a fixed number of replicas and want to turn off autoscaling.
                For example, to set a fixed number of replicas to 2, you can use: 
                --replicas-static 2  or
                -r 2
            """,
    callback=validate_autoscale_options,
)
@click.option(
    "--autoscale-down",
    "-ad",
    type=str,
    default=None,
    help="""
                Use this option if you want to have replicas but scale down after a specified time of no traffic.
                For example, to set 2 replicas and scale down after 3600 seconds of no traffic,
                use: --autoscale-down 2,3600s or --autoscale-down 2,3600
                (Note: Do not include spaces around the comma.)
            """,
    callback=validate_autoscale_options,
)
@click.option(
    "--autoscale-gpu-util",
    "-agu",
    type=str,
    default=None,
    help="""
                Use this option to set a threshold for GPU utilization and enable the system to scale between
                a minimum and maximum number of replicas. For example,
                to scale between 1 (min_replica) and 3 (max_replica) with a 50% threshold,
                use: --autoscale-between 1,3,50% or --autoscale-between 1,3,50
                (Note: Do not include spaces around the comma.)

                If the GPU utilization is higher than the target GPU utilization,
                the autoscaler will scale up the replicas.
                If the GPU utilization is lower than the target GPU utilization,
                the autoscaler will scale down the replicas.
                The threshold value should be between 0 and 99.

            """,
    callback=validate_autoscale_options,
)
@click.option(
    "--autoscale-qpm",
    "-aq",
    type=str,
    default=None,
    help="""
                Use this option to set a threshold for QPM and enable the system to scale between
                a minimum and maximum number of replicas. For example,
                to scale between 1 (min_replica) and 3 (max_replica) with a 2.5 QPM,
                use: --autoscale-between 1,3,2.5
                (Note: Do not include spaces around the comma.)

                If the QPM is higher than the target QPM,
                the autoscaler will scale up the replicas.
                If the QPM is lower than the target QPM,
                the autoscaler will scale down the replicas.
                The threshold value should be between positive number.
            """,
    callback=validate_autoscale_options,
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
    visibility,
    replicas_static,
    autoscale_down,
    autoscale_gpu_util,
    autoscale_qpm,
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
                f" [red]{WorkspaceRecord.get_current_workspace_id()}[/]."
            )
            sys.exit(1)
        records = [
            (photon.name, photon.model, photon.id_, photon.created_at)
            for photon in photons
            if photon.name == current_photon_name
        ]
        id = sorted(records, key=lambda x: x[3])[-1][2]  # type: ignore
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

    max_replicas = None
    target_gpu_utilization = 0
    no_traffic_timeout = no_traffic_timeout if no_traffic_timeout else 0
    threshold = 0
    if replicas_static:
        min_replicas = replicas_static
        max_replicas = replicas_static

    if autoscale_down:
        parts = autoscale_down.split(",")
        replicas = int(parts[0])
        timeout = int(parts[1].rstrip("s"))
        min_replicas = replicas
        max_replicas = replicas
        no_traffic_timeout = timeout

    if autoscale_gpu_util:
        parts = autoscale_gpu_util.split(",")
        min_replicas = int(parts[0])
        max_replicas = int(parts[1])
        target_gpu_utilization = int(parts[2].rstrip("%"))

    if autoscale_qpm:
        parts = autoscale_qpm.split(",")
        min_replicas = int(parts[0])
        max_replicas = int(parts[1])
        threshold = float(parts[2])

    lepton_deployment_spec = LeptonDeploymentUserSpec(
        photon_namespace="public" if public_photon else "private",
        photon_id=id,
        resource_requirement=ResourceRequirement(
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            resource_shape=resource_shape,
        ),
        api_tokens=make_token_vars_from_config(
            is_public=public,
            tokens=tokens,
        ),
        auto_scaler=AutoScaler(
            scale_down=ScaleDown(no_traffic_timeout=no_traffic_timeout),
            target_gpu_utilization_percentage=target_gpu_utilization,
            target_throughput=AutoscalerTargetThroughput(qpm=threshold),
        ),
    )

    lepton_deployment = LeptonDeployment(
        metadata=Metadata(
            id=name,
            name=name,
            visibility=LeptonVisibility(visibility) if visibility else None,
        ),
        spec=lepton_deployment_spec,
    )

    client.deployment.update(
        name_or_deployment=name,
        spec=lepton_deployment,
    )
    console.print(f"Deployment [green]{name}[/] updated.")


@deployment.command()
@click.option("--name", "-n", help="The deployment name to get status.", required=True)
def events(name):
    """
    List events of the deployment
    """
    client = APIClient()
    events = client.deployment.get_events(name)

    table = Table(title="Deployment Events", show_header=True, show_lines=False)
    table.add_column("Deployment Name")
    table.add_column("Type")
    table.add_column("Reason")
    table.add_column("Regarding")
    table.add_column("Count")
    table.add_column("Last Observed Time")
    for event in events:
        date_string = event.last_observed_time.strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(
            name,
            event.type_,
            event.reason,
            str(event.regarding),
            str(event.count),
            date_string,
        )
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(deployment)
