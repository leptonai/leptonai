import json
import os
import sys

from loguru import logger
from datetime import datetime

import click
from rich.pretty import Pretty

from rich.table import Table
from rich.text import Text

from .deployment import (
    deployment_options,
    deployment_spec_create,
)
from .job import job_spec_create, job_options
from .storage import (
    upload,
    ls,
)
from .util import (
    console,
    click_group,
)
from ..api.v1.client import APIClient
from ..api.v1.types.common import Metadata
from ..api.v1.types.tuna import L3MOptions, TunaModelSpec, TunaModel, TrainingState
from ..config import (
    DEFAULT_TUNA_TRAIN_DATASET_PATH,
    DEFAULT_TUNA_FOLDER,
    DEFAULT_TUNA_MODEL_PATH,
    TUNA_IMAGE,
    LLM_BY_LEPTON_PHOTON_NAME,
)
from ..util.util import check_name_regex


def _create_name_validator(length_limit=None):
    def _validate_name(ctx, param, value):
        full_name = value
        if not check_name_regex(full_name):
            raise click.BadParameter(
                f"Invalid name '{full_name}': Name must consist of lower case"
                " alphanumeric characters or '-', and must start with an alphabetical"
                " character and end with an alphanumeric character"
            )

        if length_limit and len(full_name) > length_limit:
            raise click.BadParameter(
                f"Invalid name '{value}':The name must be less than or equal to"
                f" {length_limit}"
            )

        return value

    return _validate_name


def _generate_info_file_name(model_name):
    return model_name + "_info.json"


def _generate_model_output_path(model_name):
    return DEFAULT_TUNA_MODEL_PATH + "/" + model_name


def _check_or_create_tuna_folder_tree():
    """Check and create the folder structure for Tuna if it does not exist."""
    client = APIClient()
    if not client.storage.check_exists(DEFAULT_TUNA_FOLDER):
        client.storage.create_dir(DEFAULT_TUNA_FOLDER)
    if not client.storage.check_exists(DEFAULT_TUNA_TRAIN_DATASET_PATH):
        client.storage.create_dir(DEFAULT_TUNA_TRAIN_DATASET_PATH)
    if not client.storage.check_exists(DEFAULT_TUNA_MODEL_PATH):
        client.storage.create_dir(DEFAULT_TUNA_MODEL_PATH)


def _model_train_completed(model_name: str) -> bool:
    """Check if the model training has been completed.

    Args:
        model_name (str): The name of the model.

    Returns:
        bool: True if training is completed, False otherwise.
    """
    client = APIClient()
    dir_infos = client.storage.get_dir(DEFAULT_TUNA_MODEL_PATH + "/" + model_name)
    return len(dir_infos) > 1


def _model_exist(model_name):
    model_output_path = _generate_model_output_path(model_name)

    client = APIClient()

    return True if client.storage.check_exists(model_output_path) else False


def _get_model(model_name):
    client = APIClient()
    tuna_models = client.tuna.get()
    for tuna_model in tuna_models:
        if tuna_model.metadata.name == model_name:
            return tuna_model
    return None


@click_group()
def tuna():
    """
    Tuna CLI: A command-line interface for dataset management, fine-tuning, and model management.

    Available Commands:

    upload-data  - Upload data to the specified remote path.

    list-data    - List all data in the default tuna train dataset path.

    remove-data  - Remove specified data file .

    train        - Create and start a new training job.

    list         - List all tuna models in this workspace.

    remove       - Delete a specified tuna model.

    run          - Run a specified tuna model.

    info         - Retrieve and print a specific tuna model information.

    clear-failed-trainings - Delete all failed training models and related jobs.
    """
    pass


@tuna.command()
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True),
    default=None,
    required=True,
    help="Local file path.",
)
@click.option(
    "--name",
    "-n",
    type=str,
    help="Enter a name for your dataset, including the file extension.",
)
@click.pass_context
def upload_data(ctx, file, name):
    """
    Uploads data to the default training dataset path specified by DEFAULT_TUNA_TRAIN_DATASET_PATH.

    Usage:
        lep tuna upload-data --file <local_file_path> --name <data_name>

    Args:
        ctx (Click.Context): The Click context object (required by Click commands).
        file (str): The local file path to the data that needs to be uploaded.
        name (str): The name to assign to the uploaded data.

    Example:
        lep tuna upload-data --file /path/to/data.csv --name training_data.csv

    Returns:
        None
    """

    _check_or_create_tuna_folder_tree()

    filename = os.path.basename(file)
    remote_file_name = name if name else filename
    file_root, file_extension = os.path.splitext(remote_file_name)

    if not check_name_regex(file_root):
        while True:
            console.print(
                f"[red]Invalid filename '{file_root}'[/]: Filename must consist of"
                " lowercase alphanumeric characters or '-', start with an alphabetical"
                " character, and end with an alphanumeric character."
            )

            name = input("Please enter a valid name with extension: ")
            new_file_root, new_file_extension = os.path.splitext(name)
            if check_name_regex(new_file_root):
                break
    else:
        name = remote_file_name

    remote_path = DEFAULT_TUNA_TRAIN_DATASET_PATH + "/" + name

    if APIClient().storage.check_exists(remote_path):
        console.print(
            f"[red]{name}[/] already exists. If you want to replace it,"
            " please use `lep tuna remove-data <data-name>` first.\nWhat you have:"
        )
        ctx.invoke(list_data)
        sys.exit(1)

    ctx.invoke(upload, local_path=file, remote_path=remote_path, suppress_output=True)
    console.print(f"Uploaded Dataset [green]{file}[/] to [green]{remote_path}[/]")


@tuna.command()
@click.pass_context
def list_data(ctx):
    """List all data in the default tuna train dataset path.

    Usage: lep tuna list-data
    """

    _check_or_create_tuna_folder_tree()

    ctx.invoke(ls, path=DEFAULT_TUNA_TRAIN_DATASET_PATH)


@tuna.command()
@click.option(
    "--name", "-n", type=click.Path(), help="Data name with extension", required=True
)
def remove_data(name):
    """Remove specified data file from the default tuna train dataset path.

    Usage: lep tuna remove-data -name <data_file_name>

    Args:
        name (str): Name of the data file to be removed.
    """
    data_file_path = DEFAULT_TUNA_TRAIN_DATASET_PATH + "/" + name
    client = APIClient()
    if not client.storage.check_exists(data_file_path):
        console.print(f"[red]Dataset {name} not found [/]")
        sys.exit(1)

    client.storage.delete_file_or_dir(data_file_path)
    console.print(f"Removed dataset [green]{name}[/].")


@tuna.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.option(
    "--name",
    "-n",
    type=str,
    help="Assign a unique identifier to your tuna model",
    required=True,
    callback=_create_name_validator(
        length_limit=33,
    ),
)
@job_options
@click.option(
    "--model-path",
    type=str,
    default=None,
    help=(
        "Specify the base model path for fine-tuning. This can be a HuggingFace model"
        " ID or a local directory path containing the model.."
    ),
    required=True,
)
@click.option(
    "--dataset-name",
    "-dn",
    type=click.Path(),
    default=None,
    help="Data path.",
    required=True,
)
@click.option(
    "--purpose",
    type=str,
    default=None,
    help="Purpose: chat, instruct. Default: chat",
    hidden=True,
)
@click.option(
    "--num-train-epochs",
    type=int,
    default=None,
    help="Number of training epochs. Default: 10",
)
@click.option(
    "--per-device-train-batch-size",
    type=int,
    default=None,
    help="Training batch size per device (GPU or CPU). Default: 32",
)
@click.option(
    "--gradient-accumulation-steps",
    type=int,
    default=None,
    help="Gradient accumulation steps. Default: 1",
)
@click.option(
    "--report-wandb",
    is_flag=True,
    help=(
        "Report to wandb. Note that WANDB_API_KEY must be set through "
        "secrets (environment variables). Default: Off"
    ),
)
@click.option(
    "--wandb-project",
    type=str,
    default=None,
    help='Wandb project (only effective when --report-wandb is set). Default: ""',
)
@click.option(
    "--learning-rate", type=float, default=None, help="Learning rate. Default: 5e-5"
)
@click.option(
    "--warmup-ratio", type=float, default=None, help="Warmup ratio. Default: 0.1"
)
@click.option(
    "--model-max-length",
    type=int,
    default=None,
    help="Maximum model length. Default: 512",
    hidden=True,
)
@click.option(
    "--lora", is_flag=True, help="Use LoRA instead of full-tuning. Default: Off"
)
@click.option(
    "--lora-rank",
    type=int,
    default=None,
    help="LoRA rank (only effective when --lora is set). Default: 8",
)
@click.option(
    "--lora-alpha",
    type=int,
    default=None,
    help="LoRA alpha. (only effective when --lora is set). Default: 16",
)
@click.option(
    "--lora-dropout",
    type=float,
    default=None,
    help="LoRA dropout. (only effective when --lora is set). Default: 0.1",
)
@click.option(
    "--medusa",
    is_flag=True,
    help="Train Medusa heads model instead of fine-tuning. Default: Off",
)
@click.option(
    "--num-medusa-head",
    type=int,
    default=None,
    help="Number of Medusa heads. (only effective when --medusa is set). Default: 4",
)
@click.option(
    "--early-stop-threshold",
    type=float,
    default=None,
    help=(
        "Early stop threshold. Default: 0.01. Stop training early if reduction in"
        " validation loss is less than the threshold for a set number of epochs."
    ),
)
@click.pass_context
def train(
    ctx,
    # Not in Cmd
    name,
    # For Job
    env,
    file,
    container_image,
    container_port,
    command,
    resource_shape,
    node_groups,
    num_workers,
    max_failure_retry,
    max_job_failure_retry,
    secret,
    mount,
    image_pull_secrets,
    intra_job_communication,
    privileged,
    ttl_seconds_after_finished,
    log_collection,
    node_ids,
    # In Cmd
    model_path,
    dataset_name,
    **kwargs,
):
    """Create and start a new training job.

    Usage: lep tuna train [OPTIONS]

    """

    data_path = DEFAULT_TUNA_TRAIN_DATASET_PATH + "/" + dataset_name

    client = APIClient()
    # Build the directory structure
    if not client.storage.check_exists(data_path):
        console.print(
            f"[red]{data_path}[/] not found. Please use "
            "lep tuna upload-data --file <local_file_path> --name <data_name> "
            "to upload your data first, and use lep tuna list-data"
            " to check your data."
        )
        sys.exit(1)

    # Generate a name for the model-data job

    # todo check whether exists
    if _model_exist(name):
        console.print(
            f"[red]{name}[/] already exist, please use another name. "
            "Currently what you have:"
        )
        ctx.invoke(list_command)
        sys.exit(1)

    client = APIClient()

    job_spec = job_spec_create(
        file=None,
        container_image=TUNA_IMAGE,
        container_port=container_port,
        resource_shape=resource_shape,
        node_groups=node_groups,
        num_workers=num_workers,
        max_failure_retry=max_failure_retry,
        max_job_failure_retry=max_job_failure_retry,
        env=env,
        secret=secret,
        mount=mount,
        image_pull_secrets=image_pull_secrets,
        intra_job_communication=intra_job_communication,
        privileged=privileged,
        ttl_seconds_after_finished=ttl_seconds_after_finished,
        log_collection=log_collection,
        node_ids=node_ids,
        is_tuna=True,
    )

    l3m_options = L3MOptions(**kwargs)

    metadata = Metadata(name=name)

    spec = TunaModelSpec(
        dataset_path=data_path,
        model_path=model_path,
        job_spec=job_spec,
        l3m_options=l3m_options,
        model_output_path=DEFAULT_TUNA_MODEL_PATH,
    )
    tuna_model = TunaModel(metadata=metadata, spec=spec)

    logger.trace(json.dumps(tuna_model.model_dump(), indent=2))
    client.tuna.train(tuna_model)

    console.print(
        f"Model Training Job for your model [green]{name}[/] created successfully."
    )


@tuna.command()
@click.option("--name", "-n", type=str, help="Model name", required=True)
def remove(name):
    """Delete a specified tuna model.

    Usage: lep tuna remove -n <model_name>

    Args:
        name (str): Name of the model to be deleted.
    """
    if not _model_exist(name):
        console.print(f"[red]{name}[/] not found.")
        sys.exit(1)

    client = APIClient()

    model = _get_model(name)
    client.tuna.delete(model.metadata.id_)
    console.print(f"Model [green]{name}[/] removed successfully")
    return


@tuna.command()
@click.option("--name", "-n", type=str, help="Model name", required=True)
@click.pass_context
def info(ctx, name):
    """
    Retrieve and print the details of a model.

    Usage: lep tuna info -n <tuna_model_name>

    Args:
        name (str): Name of the model to be deleted.
    """

    if not _model_exist(name):
        console.print(
            f"[red]{name}[/] not exist, "
            "Please use [green] lep tuna list [/] to check your models"
        )
        sys.exit(1)

    model = _get_model(name)
    model_json = model.model_dump()
    console.print(Pretty(model_json))


@tuna.command()
@click.pass_context
def clear_failed_models(ctx):
    """Delete all failed training models and related jobs.

    Usage: lep tuna clear_failed_models
    """

    client = APIClient()

    tuna_models = client.tuna.get()

    for model in tuna_models:
        if model.status.state == TrainingState.Failed:
            client.tuna.delete(model.metadata.id_)
            console.print(
                f"Training failed model [green]{model.metadata.name}[/] deleted"
                " successfully."
            )


# todo get model info / train info
# todo change time formate
@tuna.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.option(
    "--name",
    "-n",
    help="Model name, also known as the model folder name",
    required=True,
)
@click.option(
    "--hf-transfer",
    is_flag=True,
    default=True,
    help="Set to True for faster uploads and downloads from the Hub using hf_transfer.",
)
@click.option(
    "--tuna-step",
    type=int,
    default=3,
    help=""" in streaming mode, the minimum number of tokens to generate in each new chunk. 
              Smaller numbers send generated results sooner, but may lead to a slightly higher network overhead. 
              Default value set to 3. Unless you are hyper-tuning for benchmarks, you can leave this value as default.""",
)
@click.option(
    "--use-int",
    is_flag=True,
    default=True,
    help=""""Set to true to apply quantization techniques for reducing GPU memory usage. 
              For model size under 7B, or 13B with USE_INT set to true, gpu.a10 is sufficient to run the model, 
              although you might want to use more powerful computation resources.""",
)
@click.option(
    "--huggingface-token",
    type=str,
    default="HUGGING_FACE_HUB_TOKEN",
    help="""
              Name of your Hugging Face token. By default, it will be 'HUGGING_FACE_HUB_TOKEN'.
              If you haven't created it in your workspace, use:
              lep secret create -n <secret name> -v <secret value>
              """,
)
@deployment_options
@click.pass_context
def run(
    ctx,
    name,
    hf_transfer,
    tuna_step,
    use_int,
    huggingface_token,
    # For deployment
    mount,
    photon_name,
    photon_id,
    container_image,
    container_port,
    container_command,
    resource_shape,
    min_replicas,
    max_replicas,
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
    replicas_static,
    autoscale_down,
    autoscale_gpu_util,
    autoscale_qpm,
    log_collection,
    node_ids,
    # Not needed
    visibility,
):
    """Run a specified tuna model.

    Usage: lep tuna run [OPTIONS]

    Example: lep tuna run -n <tuna_model_name> --resource-shape gpu.a10

    Args:
      * name (str): Name of the model to run. (only required option)

        resource_shape (str, optional): Resource shape of the deployment.

        node_groups (tuple, optional): Node groups for the deployment.

        hf_transfer (bool, optional): Enable faster uploads and downloads from the Hub using hf_transfer.

        tuna_step (int, optional): Minimum number of tokens to generate in each new chunk in streaming mode.

        use_int (bool, optional): Apply quantization techniques for reducing GPU memory usage.

        huggingface_token (str, optional): Name of the Hugging Face token.

        mount (tuple, optional): Persistent storage to be mounted to the deployment.

        replicas_static (int, optional): Static number of replicas.

        autoscale_down (str, optional): Configuration for autoscaling down replicas.

        autoscale_gpu_util (str, optional): Configuration for autoscaling based on GPU utilization.

        autoscale_qpm (str, optional): Configuration for autoscaling based on QPM.
    """
    # use deployment create
    # todo check whether model is train completed
    _check_or_create_tuna_folder_tree()

    if not _model_exist(name):
        console.print(f"""\n[red]{name}[/] is not exist.""")
        sys.exit(1)

    if not _model_train_completed(name):
        console.print(
            f"[red]{name}[/] is either training or the training has failed. "
            "Please use [green]'lep tuna list'[/] for more information."
        )
        sys.exit(1)
    secret = list(secret)
    client = APIClient()
    secrets = client.secret.list_all()

    has_secret = False
    for cur_secret in secrets:
        if cur_secret == huggingface_token:
            has_secret = True

    if not has_secret:
        console.print(f"""[red]{huggingface_token} not exist in your secret,[/]
                        If you haven't created it in your workspace, use:
                        lep secret create -n <secret name> -v <secret value>
                        """)
        sys.exit(1)

    hf_transfer_num_str = "1" if hf_transfer else "0"
    tuna_env = [
        "HF_HUB_ENABLE_HF_TRANSFER=" + hf_transfer_num_str,
        # model_path,
        "TUNA_STREAM_CB_STEP=" + str(tuna_step),
        "USE_INT=" + str(use_int),
    ]

    env = list(env)
    env.extend(tuna_env)

    mount = list(mount)
    mount.append(f"{DEFAULT_TUNA_FOLDER}:{DEFAULT_TUNA_FOLDER}")

    secret.append(huggingface_token)
    logger.trace(secret)
    deployment_spec = deployment_spec_create(
        photon_name=LLM_BY_LEPTON_PHOTON_NAME,
        photon_id=None,
        container_image=container_image,
        container_port=container_port,
        container_command=container_command,
        resource_shape=resource_shape,
        min_replicas=min_replicas,
        max_replicas=max_replicas,
        mount=mount,
        env=env,
        secret=secret,
        public=public,
        tokens=tokens,
        no_traffic_timeout=no_traffic_timeout,
        target_gpu_utilization=target_gpu_utilization,
        initial_delay_seconds=initial_delay_seconds,
        include_workspace_token=include_workspace_token,
        rerun=rerun,
        public_photon=True,
        image_pull_secrets=image_pull_secrets,
        node_groups=node_groups,
        replicas_static=replicas_static,
        autoscale_down=autoscale_down,
        autoscale_gpu_util=autoscale_gpu_util,
        autoscale_qpm=autoscale_qpm,
        log_collection=log_collection,
        node_ids=node_ids,
    )

    # logger.trace(json.dumps(deployment_spec.model_dump(), indent=2))

    deployment_spec.envs = [
        env
        for env in deployment_spec.envs
        if (env.value not in (None, "") or env.value_from is not None)
    ]
    deployment_spec.photon_id = None
    deployment_spec.photon_namespace = None
    deployment_spec.image_pull_secrets = None
    deployment_spec.health = None
    deployment_spec.mounts = None

    tuna_model = TunaModel(
        metadata=Metadata(name=name),
        spec=TunaModelSpec(deployment_spec=deployment_spec),
    )

    logger.trace(json.dumps(tuna_model.model_dump(), indent=2))

    model = _get_model(name)

    client.tuna.run(model.metadata.id_, tuna_model)


def _get_colored_status(tuna_model):
    state = tuna_model.status.state
    state_style = (
        "green"
        if state is TrainingState.Running
        else (
            "yellow"
            if state is TrainingState.Training
            else "blue" if state is TrainingState.Ready else "red"
        )
    )
    colored_status = Text(state, style=state_style)
    return colored_status


def _get_colored_train_job_name(tuna_model, name):
    train_job_name = "Not Training"
    if tuna_model.status.state == TrainingState.Training:
        train_job_name = Text(tuna_model.status.training_jobs[0], style="green")
    elif tuna_model.status.state == TrainingState.Failed:
        train_job_name = (
            Text(tuna_model.status.training_jobs[0], style="yellow")
            if tuna_model.status.training_jobs[0] is not None
            else Text((TrainingState(name) + " (expired)"), style="red")
        )

    return train_job_name


@tuna.command(name="list")
@click.option(
    "--list-view",
    "-l",
    is_flag=True,
    default=False,
    help=(
        "Display models in a list format instead of a table. Useful for small screens."
    ),
)
@click.pass_context
def list_command(ctx, list_view):
    """
    Lists all Tuna models in the current workspace.
    Use the --list-view option to display the models in a simplified list format,
    which is particularly useful for environments with limited screen space.
    """
    client = APIClient()
    tuna_models = client.tuna.get()

    if list_view:

        for idx, tuna_model in enumerate(tuna_models):
            name = tuna_model.metadata.name
            model = tuna_model.spec.model_path
            data = tuna_model.spec.dataset_path

            lora = tuna_model.spec.l3m_options.lora
            medusa = tuna_model.spec.l3m_options.medusa
            lora_or_medusa = "LoRA" if lora else ("Medusa" if medusa else "N/A")

            create_time = tuna_model.metadata.created_at

            status = _get_colored_status(tuna_model)

            train_job_name = _get_colored_train_job_name(tuna_model, name)

            # Print model index and name without indentation
            console.print(f"[magenta]{idx}. Name:[/] {name}")

            # Print the rest of the details with indentation
            indent = " " * 4  # 4 spaces for indentation
            console.print(
                f"{indent}[magenta]Trained At:[/]"
                f" {create_time if create_time else 'N/A'}"
            )
            console.print(f"{indent}[magenta]Model:[/] {model}")
            console.print(f"{indent}[magenta]Data:[/] {data}")
            console.print(f"{indent}[magenta]Lora or Medusa:[/] {lora_or_medusa}")
            console.print(f"{indent}[magenta]State:[/]", status)
            console.print(
                f"{indent}[magenta]Deployments Name:[/]"
                f" {', '.join(tuna_model.status.deployments) if tuna_model.status.deployments else 'None'}"
            )
            console.print(f"{indent}[magenta]Train Job Name:[/] ", train_job_name)
            console.print("-" * 50)
        sys.exit(0)

    table = Table(
        show_header=True, header_style="bold magenta", show_lines=True, padding=(0, 1)
    )
    table.add_column("Name", min_width=36)
    table.add_column("Trained At")
    table.add_column("Model")
    table.add_column("Data")
    table.add_column("Lora or Medusa")
    table.add_column("State")
    table.add_column("Deployments Name")
    table.add_column("Train Job Name")

    for tuna_model in tuna_models:
        name = tuna_model.metadata.name
        model = tuna_model.spec.model_path
        data = tuna_model.spec.dataset_path

        lora = tuna_model.spec.l3m_options.lora
        medusa = tuna_model.spec.l3m_options.medusa
        lora_or_medusa = "LoRA" if lora else ("Medusa" if medusa else "N/A")

        create_time = tuna_model.metadata.created_at
        colored_status = _get_colored_status(tuna_model)

        train_job_name = _get_colored_train_job_name(tuna_model, name)

        table.add_row(
            name,
            (
                datetime.fromtimestamp(create_time / 1000).strftime("%Y-%m-%d %H:%M:%S")
                if create_time
                else "N/A"
            ),
            model,
            data,
            lora_or_medusa,
            colored_status,
            (
                "\n".join(tuna_model.status.deployments)
                if tuna_model.status.deployments
                else None
            ),
            train_job_name,
        )

    table.title = "Tuna Models"
    console.print(table)
    console.print(
        "To check the training progress, use:\n"
        "[blue]lep job log -n <training_job_name>[/]\n"
        "To check the deployment status, use:\n"
        "[blue]lep deployment status -n <deployment_name>[/]\n"
    )


def add_command(cli_group):
    cli_group.add_command(tuna)
