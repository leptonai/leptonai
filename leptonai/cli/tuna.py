import json
import os
import random
import string
import sys
import tempfile
from datetime import datetime
from enum import Enum
from typing import Optional, List

import click
from pydantic import BaseModel
from rich.pretty import Pretty

from rich.table import Table
from rich.text import Text

from .deployment import (
    create as deployment_create,
)
from .job import create as job_create
from .job import remove as job_remove
from .storage import (
    download,
    upload,
    ls,
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
)
from ..util.util import check_name_regex


class TunaModelState(str, Enum):
    Training = "Training"
    Ready = "Ready"
    Running = "Running"
    TrainFailed = "Train Failed"
    Stopped = "Stopped"
    Unknown = ""


class TunaModel(BaseModel):
    folder_name: str
    tuna_model_state: TunaModelState
    deployments: Optional[List[str]] = None
    job_name: Optional[str] = None


def _create_name_validator(prefix="", length_limit=None):
    def _validate_name(ctx, param, value):
        full_name = prefix + value
        if not check_name_regex(full_name):
            raise click.BadParameter(
                f"Invalid name '{full_name}': Name must consist of lower case"
                " alphanumeric characters or '-', and must start with an alphabetical"
                " character and end with an alphanumeric character"
            )

        if length_limit and len(full_name) > length_limit:
            raise click.BadParameter(
                f"Invalid name '{value}':The name must be less than or equal to"
                f" {length_limit - len(prefix)}"
            )

        return value

    return _validate_name


def _generate_info_file_name(model_name):
    return model_name + "_info.json"


def _generate_model_output_path(model_name):
    return DEFAULT_TUNA_MODEL_PATH + "/" + model_name


def _generate_job_name(model_name):
    return TUNA_TRAIN_JOB_NAME_PREFIX + model_name


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
    client = APIClient()
    if not client.storage.check_exists(DEFAULT_TUNA_FOLDER):
        client.storage.create_dir(DEFAULT_TUNA_FOLDER)
    if not client.storage.check_exists(DEFAULT_TUNA_TRAIN_DATASET_PATH):
        client.storage.create_dir(DEFAULT_TUNA_TRAIN_DATASET_PATH)
    if not client.storage.check_exists(DEFAULT_TUNA_MODEL_PATH):
        client.storage.create_dir(DEFAULT_TUNA_MODEL_PATH)


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

        # remove the deployment count and the deployment_name_prefix
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
        shortened_model_name_deployment_map[shortened_model_name].append(
            deployment_name + " (" + deployment.status.state + ")"
        )

    return shortened_model_name_deployment_map


def _get_model_names():
    """Retrieve the names of all models.

    Returns:
        list: List of model names.
    """
    dir_infos = APIClient().storage.get_dir(DEFAULT_TUNA_MODEL_PATH)
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
    client = APIClient()

    if not client.storage.check_exists(DEFAULT_TUNA_FOLDER):
        return {}
    if not client.storage.check_exists(DEFAULT_TUNA_MODEL_PATH):
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
                tuna_model_state=TunaModelState.TrainFailed,
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


def _get_model_details(ctx, model_name):
    """Retrieve the details of a model from its info file.

    Args:
        model_name (str): The name of the model.

    Returns:
        dict: The parameters of the model.
    """
    info_file_name = _generate_info_file_name(model_name)
    info_path = _generate_model_output_path(model_name) + "/" + info_file_name

    if not APIClient().storage.check_exists(info_path):
        return None

    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, info_file_name)

    ctx.invoke(
        download, remote_path=info_path, local_path=temp_file_path, suppress_output=True
    )

    if not os.path.exists(temp_file_path):
        raise FileNotFoundError(f"The file {temp_file_path} does not exist.")

    with open(temp_file_path, "r") as f:
        params = json.load(f)

    return params


def _get_model_key_infos(ctx, model_name):
    params = _get_model_details(ctx, model_name)

    if not params:
        return None

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
        prefix=(
            TUNA_DEPLOYMENT_NAME_PREFIX
            if len(TUNA_DEPLOYMENT_NAME_PREFIX) > len(TUNA_TRAIN_JOB_NAME_PREFIX)
            else TUNA_TRAIN_JOB_NAME_PREFIX
        ),
        length_limit=33,
    ),
)
@click.option(
    "--env",
    "-e",
    help="Environment variables to pass to the job, in the format `NAME=VALUE`.",
    multiple=True,
)
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
    # not in cmd
    name,
    # in cmd
    env,
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
            f"[red]{data_path}[/] not found. Please use lep tuna upload-data -l"
            " <local_file_path>to upload your data first, and use lep tuna list-data"
            " to check your data."
        )
        sys.exit(1)

    # Generate a name for the model-data job

    model_output_path = _generate_model_output_path(name)

    if client.storage.check_exists(model_output_path):
        console.print(
            f"[red]{name}[/] already exist, please use another name. "
            "Currently what you have:"
        )
        ctx.invoke(list_command)
        sys.exit(1)

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
        "model_path": model_path,
        "dataset_file_name": dataset_name,
        "output_dir": model_output_path,
        "env": [env_element.split("=")[0] + "=<---secret--->" for env_element in env],
        "created_time": datetime.now().isoformat(),
        **kwargs,
    }

    # Generate the output folder
    APIClient().storage.create_dir(model_output_path)
    model_info_file_name = _generate_info_file_name(name)

    model_info_file_path = _save_params_to_json(params, model_info_file_name)

    ctx.invoke(
        upload,
        local_path=model_info_file_path,
        remote_path=model_output_path + "/" + model_info_file_name,
        suppress_output=True,
    )
    # Build mount variable
    mount = [f"{DEFAULT_TUNA_FOLDER}:{DEFAULT_TUNA_FOLDER}"]

    update_args = [
        "--name",
        job_name,
        "--command",
        cmd,
        "--container-image",
        TUNA_IMAGE,
    ]

    for env_element in env:
        update_args.extend(["--env", env_element])
    for mount_element in mount:
        update_args.extend(["--mount", mount_element])

    combined_args = ctx.args + update_args
    job_create_ctx = job_create.make_context(info_name="create", args=combined_args)
    ctx.invoke(job_create, **job_create_ctx.params)
    console.print(
        f"Model Training Job [green]{job_name}[/] for your model"
        f" [green]{name}[/] created successfully."
    )


@tuna.command()
@click.option("--name", "-n", type=str, help="Model name", required=True)
def remove(name):
    """Delete a specified tuna model.

    Usage: lep tuna remove -n <model_name>

    Args:
        name (str): Name of the model to be deleted.
    """
    models_map = _get_models_map()

    if name not in models_map:
        models_name = models_map.keys()
        console.print(f"""
            [red]{name}[/] not found.
        """)
        if len(models_name) != 0:
            models_str = "\n                ".join(models_name)
            console.print(f"""what you have is:
                [green]{models_str}[/]""")
        sys.exit(1)
    cur_tuna_model = models_map[name]

    if cur_tuna_model.deployments is not None and len(cur_tuna_model.deployments) > 0:
        deployments_list = "\n            ".join(cur_tuna_model.deployments)
        console.print(f"""
            The model '{name}' is currently [red]{cur_tuna_model.tuna_model_state}[/].
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
        if user_input not in ["yes", "y"]:
            sys.exit(0)
    elif _model_train_completed(name):
        console.print(
            f"[red]The model '{name}' is ready and has been trained successfully.[/]"
        )
        user_input = (
            input("Do you want to delete this model? (yes/no): ").strip().lower()
        )
        if user_input not in ["yes", "y"]:
            sys.exit(0)

    client = APIClient()
    jobs = client.job.list_all()
    job_name = _generate_job_name(name)
    for job in jobs:
        if job.metadata.name == job_name:
            client.job.delete(job_name)

    if cur_tuna_model.deployments is not None and len(cur_tuna_model.deployments) > 0:
        client = APIClient()
        for deployment in cur_tuna_model.deployments:
            deployment_name = deployment.split(" ")[0]
            client.deployment.delete(deployment_name)
            console.print(f"Deployment [green]{name}[/] deleted successfully.")

    model_path = _generate_model_output_path(name)
    # model_path = DEFAULT_TUNA_MODEL_PATH + "/" + model_folder_name

    APIClient().storage.delete_file_or_dir(model_path, delete_all=True)
    console.print(f"Model [green]{name}[/] deleted successfully.")


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
    models_names = _get_model_names()
    if name not in models_names:
        console.print(
            f"[red]{name}[/] not exist, "
            "Please use [green] lep tuna list [/] to check your models"
        )
        sys.exit(1)
    params = _get_model_details(ctx, name)

    console.print(f"Model information for [yellow]'{name}'[/]：")

    console.print(Pretty(params))


@tuna.command()
@click.pass_context
def clear_failed_models(ctx):
    """Delete all failed training models and related jobs.

    Usage: lep tuna clear_failed_models
    """
    for model_name, tuna_model in _get_models_map().items():
        if tuna_model.tuna_model_state is TunaModelState.TrainFailed:
            model_path = _generate_model_output_path(model_name)
            APIClient().storage.delete_file_or_dir(model_path, delete_all=True)
            if tuna_model.job_name:
                ctx.invoke(job_remove, name=tuna_model.job_name)
            console.print(
                f"Training failed model [green]{model_name}[/] deleted successfully."
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
@click.option(
    "--mount",
    help=(
        "Persistent storage to be mounted to the deployment, in the format"
        " `STORAGE_PATH:MOUNT_PATH`."
    ),
    multiple=True,
)
@click.pass_context
def run(
    ctx,
    name,
    hf_transfer,
    tuna_step,
    use_int,
    huggingface_token,
    mount,
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
            "Please use [green]'lep tuna list'[/] for more information."
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

    base_model_path, data, lora_or_medusa, create_time = _get_model_key_infos(ctx, name)

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

    update_args = [
        "--name",
        deployment_name,
        "--photon",
        LLM_BY_LEPTON_PHOTON_NAME,
        "--secret",
        huggingface_token,
        "--public-photon",
    ]
    for env_element in env:
        update_args.extend(["--env", env_element])
    for mount_element in mount:
        update_args.extend(["--mount", mount_element])

    combined_args = ctx.args + update_args
    deployment_create_ctx = deployment_create.make_context(
        info_name="create", args=combined_args
    )
    ctx.invoke(deployment_create, **deployment_create_ctx.params)


def _get_colored_status(tuna_model):
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
    colored_status = Text(status, style=state_style)
    return colored_status


def _get_colored_train_job_name(tuna_model, name):
    train_job_name = "Not Training"
    if tuna_model.tuna_model_state == TunaModelState.Training:
        train_job_name = Text(tuna_model.job_name, style="green")
    elif tuna_model.tuna_model_state == TunaModelState.TrainFailed:
        train_job_name = (
            Text(tuna_model.job_name, style="yellow")
            if tuna_model.job_name is not None
            else Text((_generate_job_name(name) + " (expired)"), style="red")
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

    if list_view:
        for idx, (name, tuna_model) in enumerate(_get_models_map().items(), start=1):
            key_infos = _get_model_key_infos(ctx, name)
            if not key_infos:
                continue
            model, data, lora_or_medusa, create_time = key_infos
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
                f" {', '.join(tuna_model.deployments) if tuna_model.deployments else 'None'}"
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

    for name, tuna_model in _get_models_map().items():
        key_infos = _get_model_key_infos(ctx, name)
        if not key_infos:
            continue
        model, data, lora_or_medusa, create_time = key_infos

        colored_status = _get_colored_status(tuna_model)

        train_job_name = _get_colored_train_job_name(tuna_model, name)

        table.add_row(
            name,
            create_time if create_time else "N/A",
            model,
            data,
            lora_or_medusa,
            colored_status,
            "\n".join(tuna_model.deployments) if tuna_model.deployments else None,
            train_job_name,
        )

    table.title = "Tuna Models"
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(tuna)
