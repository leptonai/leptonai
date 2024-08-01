import json
import os
import random
import re
import string
import sys
import tempfile
import time
from datetime import datetime
from enum import Enum
from typing import Optional, List

import click
from pydantic import BaseModel
from rich.pretty import Pretty

from rich.table import Table
from rich.text import Text

from .deployment import deployment_create, validate_autoscale_options, deployment_remove
from .job import job_create, job_remove
from .storage import (
    storage_upload,
    storage_find,
    storage_mkdir,
    storage_ls,
    storage_rm,
    storage_rmdir,
    storage_download,
)
from .util import (
    console,
    click_group,
)
from ..api.v1.client import APIClient
from ..api.v1.types.deployment import LeptonDeploymentState
from ..api.v1.types.job import LeptonJobState
from ..config import (
    DEFAULT_TUNA_TRAIN_DATASET_PATH,
    DEFAULT_TUNA_FOLDER,
    DEFAULT_TUNA_MODEL_PATH,
    TUNA_TRAIN_JOB_NAME_PREFIX,
    TUNA_IMAGE,
    TUNA_DEPLOYMENT_NAME_PREFIX,
    LLM_BY_LEPTON_PHOTON_NAME,
    DEFAULT_RESOURCE_SHAPE,
)


class TunaModelState(str, Enum):
    Training = "Training"
    Ready = "Ready"
    Running = "Running"
    trainFailed = "Train Failed"
    Stopped = "Stopped"
    Unknown = ""


class TunaModel(BaseModel):
    folder_name: str
    tuna_model_state: TunaModelState
    deployments: Optional[List[str]] = None
    job_name: Optional[str] = None


def _validate_name(ctx, param, value):
    if not re.match(r"^[a-z0-9-]+$", value):
        raise click.BadParameter(
            'Name must contain only alphanumeric characters and "-"'
        )
    if value.endswith("-"):
        raise click.BadParameter('Name cannot end with "-"')
    return value


def _timestamp_to_readable(timestamp):
    """Convert a timestamp in milliseconds to a readable datetime format.

    Args:
        timestamp (int): Timestamp in milliseconds
        --- time.time() * 1000

    Returns:
        str: Readable datetime string.
    """
    # Convert milliseconds to seconds
    timestamp_seconds = timestamp / 1000

    dt = datetime.fromtimestamp(timestamp_seconds)

    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _generate_info_file_name(model_name):
    return model_name + "_info.json"


def _generate_model_output_path(model_name):
    return DEFAULT_TUNA_MODEL_PATH + "/" + model_name


def _generate_job_name(model_name):
    job_name = (TUNA_TRAIN_JOB_NAME_PREFIX + model_name)[:36]
    return job_name if not job_name.endswith("-") else job_name[:-1]


# def _generate_model_name(model_path, data_filename, is_lora=False, is_medusa=False):
#     """Generate a unique model name based on various parameters.
#
#     Args:
#         model_path (str): The path of the model.
#         data_filename (str): The name of the data file.
#         is_lora (bool): Whether LoRA is used.
#         is_medusa (bool): Whether Medusa is used.
#
#     Returns:
#         str: The generated model name.
#     """
#     # Remove all non-alphanumeric characters
#     model_filename_clean = model_path.split("/")[-1]
#     model_filename_clean = re.sub(r"\W+", "", model_filename_clean).lower()
#     data_filename_clean = re.sub(r"\W+", "", data_filename)
#
#     # Get the current date and time
#     current_datetime = int(time.time() * 1000)
#
#     # Concatenate the strings
#     result_string = f"{current_datetime}-{model_filename_clean}-{data_filename_clean}"
#
#     if is_lora:
#         result_string += "-lora"
#     elif is_medusa:
#         result_string += "-medusa"
#     # make sure the length of the name is less than 32
#     return result_string
#


def _save_params_to_json(params, filename):
    """Save parameters to a JSON file.

    Args:
        params (dict): Parameters to be saved.
        filename (str): Optional filename for the JSON file.

    Returns:
        str: The path of the saved JSON file.
    """
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, filename)

    # Save parameters to the JSON file
    with open(temp_file_path, "w") as f:
        json.dump(params, f, indent=4)

    return temp_file_path


def _check_or_create_tuna_folder_tree():
    """Check and create the folder structure for Tuna if it does not exist."""
    if not storage_find(DEFAULT_TUNA_FOLDER):
        storage_mkdir(DEFAULT_TUNA_FOLDER)
    if not storage_find(DEFAULT_TUNA_TRAIN_DATASET_PATH):
        storage_mkdir(DEFAULT_TUNA_TRAIN_DATASET_PATH)
    if not storage_find(DEFAULT_TUNA_MODEL_PATH):
        storage_mkdir(DEFAULT_TUNA_MODEL_PATH)


def _generate_model_deployment_name(model_name):
    """Generate a deployment name for the model.

    Args:
        model_name (str): The name of the model.

    Returns:
        str: The generated deployment name.
    """
    client = APIClient()
    deployments = client.deployment.list_all()
    deployment_names_set = {deployment.metadata.name for deployment in deployments}
    base_name = TUNA_DEPLOYMENT_NAME_PREFIX + model_name
    counter = 0
    for i in range(0, 999):
        new_name = f"{base_name[:36 - (len(str(counter)) + 1)]}-{counter}"
        if new_name not in deployment_names_set:
            return new_name
        counter += 1
    random_string = "".join(random.choices(string.ascii_letters + string.digits, k=4))
    return (TUNA_DEPLOYMENT_NAME_PREFIX + model_name)[:32] + random_string


def _build_shortened_model_name_deployment_map():
    """Build a map of shortened model names to deployment information.

    Returns:
        dict: Mapping of shortened model names to deployment information.
    """
    client = APIClient()
    deployments = client.deployment.list_all()
    shortened_model_name_deployment_map = {}

    for deployment in deployments:
        deployment_name = deployment.metadata.name
        if TUNA_DEPLOYMENT_NAME_PREFIX not in deployment_name:
            continue
        shortened_model_name = deployment_name[: deployment_name.rindex("-")][
            len(TUNA_DEPLOYMENT_NAME_PREFIX) :
        ]
        if deployment.status.state in [
            LeptonDeploymentState.Ready,
            LeptonDeploymentState.Starting,
            LeptonDeploymentState.Updating,
        ]:
            if shortened_model_name not in shortened_model_name_deployment_map:
                shortened_model_name_deployment_map[shortened_model_name] = [
                    TunaModelState.Running
                ]
            else:
                shortened_model_name_deployment_map[shortened_model_name][
                    0
                ] = TunaModelState.Running

        elif shortened_model_name not in shortened_model_name_deployment_map:
            shortened_model_name_deployment_map[shortened_model_name] = [
                TunaModelState.Stopped
            ]
        else:
            shortened_model_name_deployment_map[shortened_model_name][
                0
            ] = TunaModelState.Stopped

        shortened_model_name_deployment_map[shortened_model_name].append(
            deployment_name + " (" + deployment.status.state + ")"
        )

    return shortened_model_name_deployment_map


def _get_model_names():
    """Retrieve the names of all models.

    Returns:
        list: List of model names.
    """
    dir_infos = storage_ls(DEFAULT_TUNA_MODEL_PATH, do_print=False)
    model_names = []
    for dir_info in dir_infos:
        if dir_info.type == "dir":
            model_names.append(dir_info.name)
    return model_names


def _get_models_map():
    """Get a map of model names to TunaModel instances.

    Returns:
        dict: Mapping of model names to TunaModel instances.
    """
    if not storage_find(DEFAULT_TUNA_FOLDER):
        return {}
    if not storage_find(DEFAULT_TUNA_MODEL_PATH):
        return {}

    client = APIClient()

    jobs = client.job.list_all()
    running_job_set = set()
    failed_job_set = set()
    for job in jobs:
        job_status = job.status.state
        if (
            job_status is LeptonJobState.Running
            or job_status is LeptonJobState.Starting
        ):
            running_job_set.add(job.metadata.name)
        elif job_status is LeptonJobState.Failed:
            failed_job_set.add(job.metadata.name)

    model_deployment_map = _build_shortened_model_name_deployment_map()

    model_names = _get_model_names()
    model_names_map = {}
    for model_name in model_names:
        job_name = _generate_job_name(model_name)

        if not _model_train_completed(model_name) and job_name not in running_job_set:
            model_names_map[model_name] = TunaModel(
                folder_name=model_name,
                tuna_model_state=TunaModelState.trainFailed,
            )
            if job_name in failed_job_set:
                model_names_map[model_name].job_name = job_name

        elif job_name not in running_job_set:
            cur_shorten_model_name = model_name[: 32 - len(TUNA_DEPLOYMENT_NAME_PREFIX)]
            if cur_shorten_model_name in model_deployment_map:
                cur_deployment_info = model_deployment_map[cur_shorten_model_name]
                model_names_map[model_name] = TunaModel(
                    folder_name=model_name,
                    deployments=cur_deployment_info[1:],
                    tuna_model_state=cur_deployment_info[0],
                )
            else:
                model_names_map[model_name] = TunaModel(
                    folder_name=model_name,
                    tuna_model_state=TunaModelState.Ready,
                )
        else:
            model_names_map[model_name] = TunaModel(
                folder_name=model_name,
                tuna_model_state=TunaModelState.Training,
                job_name=job_name,
            )
    return model_names_map


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


def _get_model_name_from_job(job_name):
    """Get the model name associated with a job.

    Args:
        job_name (str): The name of the job.

    Returns:
        str: The name of the model.
    """
    job_name = job_name[len(TUNA_TRAIN_JOB_NAME_PREFIX) :]
    models_names = _get_model_names()
    for model_name in models_names:
        if job_name in model_name:
            return model_name


def _get_model_details(model_name):
    """Retrieve the details of a model from its info file.

    Args:
        model_name (str): The name of the model.

    Returns:
        dict: The parameters of the model.
    """
    info_file_name = _generate_info_file_name(model_name)
    info_path = _generate_model_output_path(model_name) + "/" + info_file_name
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, info_file_name)

    storage_download(info_path, temp_file_path)

    if not os.path.exists(temp_file_path):
        raise FileNotFoundError(f"The file {temp_file_path} does not exist.")

    with open(temp_file_path, "r") as f:
        params = json.load(f)

    return params


def _get_model_key_infos(model_name):
    params = _get_model_details(model_name)
    create_time = params.get("created_time")
    model_path = params.get("model_path")
    data = params.get("dataset_file_name")
    lora_or_medusa = (
        "lora" if params.get("lora") else ("medusa" if params.get("medusa") else None)
    )

    return model_path, data, lora_or_medusa, create_time


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
    "--local-path",
    "-l",
    type=click.Path(exists=True),
    default=None,
    required=True,
    help="Local data path.",
)
@click.option(
    "--name",
    "-n",
    type=str,
    help=(
        "Provide a name for your dataset. Only the name is needed; the file extension"
        " will be determined automatically based on the local file type."
    ),
    required=True,
    callback=_validate_name,
)
@click.option(
    "--for-test-remote-path",
    type=click.Path(),
    default=None,
    help="Remote folder path.",
)
def upload_data(local_path, name, for_test_remote_path):
    """Upload data to the DEFAULT_TUNA_TRAIN_DATASET_PATH path.

    Usage: lep tuna upload-data --local-path <local_path>

    Args:
        local_path (str): Local data path.
        for_test_remote_path (str): Remote folder path. This option is intended for testing purposes only.
    """
    _check_or_create_tuna_folder_tree()

    if not for_test_remote_path:
        for_test_remote_path = DEFAULT_TUNA_TRAIN_DATASET_PATH

    filename = os.path.basename(local_path)
    file_root, file_extension = os.path.splitext(filename)
    remote_path = for_test_remote_path + "/" + name + file_extension

    if storage_find(remote_path):
        console.print(
            f"[red]{name}{file_extension}[/] already exists. If you want to replace it,"
            " please use `lep tuna remove-data <data-name>` first.\nWhat you have:"
        )
        tuna_list_data()
        sys.exit(1)

    storage_upload(
        local_path,
        remote_path,
    )
    console.print(f"Uploaded Dataset [green]{local_path}[/] to [green]{remote_path}[/]")


@tuna.command()
def list_data():
    """List all data in the default tuna train dataset path.

    Usage: lep tuna list-data
    """

    tuna_list_data()


def tuna_list_data():
    _check_or_create_tuna_folder_tree()

    storage_ls(DEFAULT_TUNA_TRAIN_DATASET_PATH)


@tuna.command()
@click.argument(
    "data_file_name",
    type=click.Path(),
    required=True,
)
def remove_data(data_file_name):
    """Remove specified data file from the default tuna train dataset path.

    Usage: lep tuna remove-data --data-file-name <data_file_name>

    Args:
        data_file_name (str): Name of the data file to be removed.
    """
    data_file_path = DEFAULT_TUNA_TRAIN_DATASET_PATH + "/" + data_file_name
    if not storage_find(data_file_path):
        console.print(f"[red]Dataset {data_file_name} not found [/]")
        sys.exit(1)

    storage_rm(data_file_path)
    console.print(f"Removed dataset [green]{data_file_name}[/].")


@tuna.command()
@click.option(
    "--name",
    "-n",
    type=str,
    help="Assign a unique identifier to your tuna model",
    required=True,
    callback=_validate_name,
)
@click.option(
    "--resource-shape",
    type=str,
    help="Resource shape for the job.",
    default=None,
)
@click.option(
    "--node-group",
    "-ng",
    "node_groups",
    help="Node group for the job. If not set, use on-demand resources.",
    type=str,
    multiple=True,
)
@click.option(
    "--num-workers",
    "-w",
    help=(
        "Number of workers to use for the job. For example, when you do a distributed"
        " training job of 4 replicas, use --num-workers 4."
    ),
    type=int,
    default=None,
)
@click.option(
    "--max-job-failure-retry",
    type=int,
    help="Maximum number of failures to retry per whole job.",
    default=None,
)
@click.option(
    "--env",
    "-e",
    help="Environment variables to pass to the job, in the format `NAME=VALUE`.",
    multiple=True,
)
@click.option(
    "--model-path", type=click.Path(), default=None, help="Model path.", required=True
)
@click.option(
    "--dataset-file-name",
    "-dn",
    type=click.Path(),
    default=None,
    help="Data path.",
    required=True,
)
@click.option(
    "--purpose", type=str, default=None, help="Purpose: Chat, Instruct. Default: Chat"
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
    help="Training batch size. Default: 32",
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
    "--save-steps", type=int, default=None, help="Model save steps. Default: 500"
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
    help="Early stop threshold. Default: 0.01",
)
def train(
    # not in cmd
    name,
    node_groups,
    num_workers,
    max_job_failure_retry,
    # in cmd
    resource_shape,
    env,
    model_path,
    dataset_file_name,
    **kwargs,
):
    """Create and start a new training job.

    Usage: lep tuna train [OPTIONS]
    """

    data_path = DEFAULT_TUNA_TRAIN_DATASET_PATH + "/" + dataset_file_name

    # Build the directory structure
    if not storage_find(data_path):
        console.print(
            f"[red]{data_path}[/] not found. Please use lep tuna upload-data -l"
            " <local_file_path>to upload your data first, and use lep tuna list-data"
            " to check your data."
        )
        sys.exit(1)

    # Generate a name for the model-data job

    model_output_path = _generate_model_output_path(name)

    if storage_find(model_output_path):
        console.print(
            f"[red]{name}[/] already exist, please use another name. "
            "Currently what you have:"
        )
        tuna_list()
        sys.exit(1)

    # name = _generate_model_name(
    #     model_path, dataset_file_name, kwargs.get("lora"), kwargs.get("medusa")
    # )
    job_name = _generate_job_name(name)

    client = APIClient()
    jobs = client.job.list_all()
    for job in jobs:
        if job.metadata.name == job_name:
            console.print(
                f"Failed to create training job [red]{job_name}[/]: The job already"
                " exists. Please either delete the existing job if it's no longer"
                " needed, or change your model name."
            )
            sys.exit(1)

    # Construct the command string
    cmd = (
        "run_training"
        f" --model_name_or_path={model_path} --data_path={data_path} --output_dir={model_output_path}"
    )
    for key, value in kwargs.items():
        if value is not None:
            option = f"--{key}"
            if isinstance(value, bool):
                if value:
                    cmd += f" {option}"
            elif isinstance(value, str):
                cmd += f' {option}="{value}"'
            else:
                cmd += f" {option}={value}"
    # Save all parameters to a JSON file and upload to model path

    params = {
        "name": name,
        "train_job_name": job_name,
        "resource_shape": resource_shape,
        "node_groups": node_groups,
        "num_workers": num_workers,
        "max_job_failure_retry": max_job_failure_retry,
        "model_path": model_path,
        "dataset_file_name": dataset_file_name,
        "output_dir": model_output_path,
        "env": [env_element.split("=")[0] + "=<---secret--->" for env_element in env],
        "created_time": datetime.now().isoformat(),
        **kwargs,
    }

    # Generate the output folder
    storage_mkdir(model_output_path)
    model_info_file_name = _generate_info_file_name(name)

    model_info_file_path = _save_params_to_json(params, model_info_file_name)

    storage_upload(model_info_file_path, model_output_path + "/" + model_info_file_name)
    # Build mount variable
    mount = [f"{DEFAULT_TUNA_FOLDER}:{DEFAULT_TUNA_FOLDER}"]

    job_create(
        job_name,
        command=cmd,
        mount=mount,
        resource_shape=resource_shape,
        node_groups=node_groups,
        num_workers=num_workers,
        max_job_failure_retry=max_job_failure_retry,
        env=env,
        container_image=TUNA_IMAGE,
    )
    console.print(
        f"Model Training Job [green]{job_name}[/] for your model"
        f" [green]{name}[/] created successfully."
    )


@tuna.command()
@click.argument("model_name")
def remove(model_name):
    """Delete a specified tuna model.

    Usage: lep tuna remove <model_name>

    Args:
        model_name (str): Name of the model to be deleted.
    """
    models_map = _get_models_map()

    if model_name not in models_map:
        models_name = models_map.keys()
        console.print(f"""
            [red]{model_name}[/] not found.
        """)
        if len(models_name) != 0:
            models_str = "\n                ".join(models_name)
            console.print(f"""what you have is:
                [green]{models_str}[/]""")
        sys.exit(1)
    cur_tuna_model = models_map[model_name]

    if cur_tuna_model.deployments is not None and len(cur_tuna_model.deployments) > 0:
        deployments_list = "\n            ".join(cur_tuna_model.deployments)
        console.print(f"""
            The model '{model_name}' is currently [red]{cur_tuna_model.tuna_model_state}[/].
            It has the following deployments: 
            [green]{deployments_list}[/].
            """)
        user_input = (
            input(
                "Are you sure you want to delete all the deployments and then delete"
                " the tuna model? (yes/no): "
            )
            .strip()
            .lower()
        )
        if user_input == "no":
            sys.exit(0)
    elif _model_train_completed(model_name):
        console.print(
            f"[red]The model '{model_name}' is ready and has been trained"
            " successfully.[/]"
        )
        user_input = (
            input("Do you want to delete this model? (yes/no): ").strip().lower()
        )
        if user_input == "no":
            sys.exit(0)

    client = APIClient()
    jobs = client.job.list_all()
    job_name = _generate_job_name(model_name)
    for job in jobs:
        if job.metadata.name == job_name:
            client.job.delete(job_name)

    if cur_tuna_model.deployments is not None and len(cur_tuna_model.deployments) > 0:
        for deployment in cur_tuna_model.deployments:
            deployment_name = deployment.split(" ")[0]
            deployment_remove(deployment_name)

    model_path = _generate_model_output_path(model_name)
    # model_path = DEFAULT_TUNA_MODEL_PATH + "/" + model_folder_name

    storage_rmdir(model_path, delete_all=True)
    console.print(f"Model [green]{model_name}[/] deleted successfully.")


@tuna.command()
@click.argument("model_name")
def info(model_name):
    """
    Retrieve and print the details of a model.

    Usage: lep tuna info <tuna_model_name>
    """
    models_names = _get_model_names()
    if model_name not in models_names:
        console.print(
            f"[red]{model_name}[/] not exist, "
            "Please use [green] lep tuna list [/] to check your models"
        )
        sys.exit(1)
    params = _get_model_details(model_name)

    console.print(f"Model information for [yellow]'{model_name}'[/]：")

    console.print(Pretty(params))


@tuna.command()
def clear_failed_trainings():
    """Delete all failed training models and related jobs.

    Usage: lep tuna clear-failed-trainings
    """
    for model_name, tuna_model in _get_models_map().items():
        if tuna_model.tuna_model_state is TunaModelState.trainFailed:
            model_path = _generate_model_output_path(model_name)
            storage_rmdir(model_path, delete_all=True)
            if tuna_model.job_name:
                job_remove(tuna_model.job_name)
            console.print(
                f"Training failed model [green]{model_name}[/] deleted successfully."
            )


# todo get model info / train info
# todo change time formate
@tuna.command()
@click.option(
    "--name", "-n", help="--name, also known as the model folder name", required=True
)
@click.option(
    "--resource-shape",
    "-rs",
    default=DEFAULT_RESOURCE_SHAPE,
    help="Resource shape of the deployment",
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
@click.option(
    "--mount",
    help=(
        "Persistent storage to be mounted to the deployment, in the format"
        " `STORAGE_PATH:MOUNT_PATH`."
    ),
    multiple=True,
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
def run(
    name,
    resource_shape,
    node_groups,
    hf_transfer,
    tuna_step,
    use_int,
    huggingface_token,
    mount,
    replicas_static=None,
    autoscale_down=None,
    autoscale_gpu_util=None,
    autoscale_qpm=None,
):
    """Run a specified tuna model.

    Usage: lep tuna run [OPTIONS]

    Args:
      * name (str): Name of the model to run. (only required option)

        resource_shape (str, optional): Resource shape of the deployment. default will be {DEFAULT_RESOURCE_SHAPE}

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

    names = _get_model_names()
    model_list = "\n                      ".join(names)
    if name not in names:
        console.print(f"""\n[red]{name}[/] is not exist. what you have:
                      [green]{model_list}[/]
                      """)
        sys.exit(1)

    if not _model_train_completed(name):
        console.print(
            f"[red]{name}[/] is either training or the training has failed. "
            "Please use 'lep tuna list' for more information."
        )
        sys.exit(1)

    client = APIClient()
    secrets = client.secret.list_all()

    has_secret = False
    for secret in secrets:
        if secret == huggingface_token:
            has_secret = True

    if not has_secret:
        console.print(f"""[red]{huggingface_token} not exist in your secret,[/]
                        If you haven't created it in your workspace, use:
                        lep secret create -n <secret name> -v <secret value>
                        """)
        sys.exit(1)

    deployment_name = _generate_model_deployment_name(name)

    model_output_path = _generate_model_output_path(name)

    base_model_path, data, lora_or_medusa, create_time = _get_model_key_infos(name)

    lora = None
    medusa = None
    if lora_or_medusa == "lora":
        model_path = "MODEL_PATH=" + base_model_path
        lora = f"LORAS={model_output_path}:{name}"
    elif lora_or_medusa == "medusa":
        model_path = "MODEL_PATH=" + base_model_path
        medusa = "MEDUSA=" + model_output_path
    else:
        model_path = "MODEL_PATH=" + model_output_path
    hf_transfer_num_str = "1" if hf_transfer else "0"
    env = [
        "HF_HUB_ENABLE_HF_TRANSFER=" + hf_transfer_num_str,
        model_path,
        "TUNA_STREAM_CB_STEP=" + str(tuna_step),
        "USE_INT=" + str(use_int),
    ]
    if lora:
        env.append(lora)
    if medusa:
        env.append(medusa)

    mount = list(mount)
    mount.append("/lepton-tuna:/lepton-tuna")

    huggingface_token = [huggingface_token]

    deployment_create(
        name=deployment_name,
        resource_shape=resource_shape,
        photon_name=LLM_BY_LEPTON_PHOTON_NAME,
        env=env,
        node_groups=node_groups,
        secret=huggingface_token,
        mount=mount,
        public_photon=True,
        replicas_static=replicas_static,
        autoscale_down=autoscale_down,
        autoscale_gpu_util=autoscale_gpu_util,
        autoscale_qpm=autoscale_qpm,
    )


@tuna.command(name="list")
def list_command():
    """
    Lists all tuna model in this workspace.
    """

    tuna_list()


def tuna_list():
    table = Table(
        show_header=True, header_style="bold magenta", show_lines=True, padding=(0, 1)
    )
    table.add_column("Name")
    table.add_column("Trained At")
    table.add_column("Model")
    table.add_column("Data")
    table.add_column("Lora or Medusa")
    table.add_column("State (Training, Ready, Running, Stopped, Train Failed)")
    table.add_column("Running Deployments Name")
    table.add_column("Train Job Name")

    for name, tuna_model in _get_models_map().items():
        model, data, lora_or_medusa, create_time = _get_model_key_infos(name)
        # params = _get_model_details(name)
        # create_time = params.get("created_time")
        # model = params.get("model_path")
        # data = params.get("dataset_file_name")
        # lora_or_medusa = "lora" if params.get("lora") else ("medusa" if params.get("medusa") else None)

        # create_time, model, data, lora_or_medusa = _get_model_basic_info_from_model_name(
        #     model_name=name
        # )
        status = tuna_model.tuna_model_state
        state_style = (
            "green"
            if status is TunaModelState.Running
            else (
                "yellow"
                if status is TunaModelState.Training
                else "blue" if status is TunaModelState.Ready else "red"
            )
        )

        train_job_name = "Not Training"
        if tuna_model.tuna_model_state == TunaModelState.Training:
            train_job_name = Text(tuna_model.job_name, style="green")
        elif tuna_model.tuna_model_state == TunaModelState.trainFailed:
            train_job_name = (
                Text(tuna_model.job_name, style="yellow")
                if tuna_model.job_name is not None
                else Text((_generate_job_name(name) + " (expired)"), style="red")
            )

        table.add_row(
            name,
            create_time if create_time else "N/A",
            model,
            data,
            lora_or_medusa,
            Text(status, style=state_style),
            "\n".join(tuna_model.deployments) if tuna_model.deployments else None,
            train_job_name,
        )

    table.title = "Tuna Models"
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(tuna)
