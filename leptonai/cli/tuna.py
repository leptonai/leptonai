import json
import os
import re
import sys
import tempfile
from datetime import datetime

import click
from loguru import logger

from rich.table import Table

from .job import job_create
from .storage import storage_upload, storage_find, storage_mkdir, storage_ls, storage_rm, storage_rmdir
from .util import (
    console,
    click_group,
)
from ..api.v1.client import APIClient
from ..api.v1.types.job import LeptonJobState
from ..config import (
    DEFAULT_TUNA_TRAIN_DATASET_PATH,
    DEFAULT_TUNA_FOLDER,
    DEFAULT_TUNA_MODEL_PATH,
    TUNA_TRAIN_JOB_NAME_PREFIX,
    TUNA_IMAGE,
)


def _generate_model_folder_name(model_path, data_filename):
    # Remove all non-alphanumeric characters
    model_filename_clean = model_path.split("/")[-1]
    model_filename_clean = re.sub(r"\W+", "", model_filename_clean).lower()
    data_filename_clean = re.sub(r"\W+", "", data_filename)

    # Get the current date and time
    current_datetime = datetime.now().strftime("%Y%m%d%H%M%S")[2:]

    # Concatenate the strings
    result_string = f"{current_datetime}-{model_filename_clean}-{data_filename_clean}"

    # make sure the length of the name is less than 32
    return result_string


def _get_job_name(model_folder_name):
    return (TUNA_TRAIN_JOB_NAME_PREFIX + model_folder_name)[:36]


def _save_params_to_json(params, filename=None):
    if filename is None:
        # Create a temporary file if no filename is provided
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        temp_file_path = temp_file.name
    else:
        # Use the provided filename and create the file in a temporary directory
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, filename)

    # Save parameters to the JSON file
    with open(temp_file_path, "w") as f:
        json.dump(params, f, indent=4)

    return temp_file_path, filename


def reverse_datetime(current_datetime):
    # current_datetime format is '240718124530'
    year = '20' + current_datetime[:2]  # Prefix '20' to the first two characters
    month = current_datetime[2:4]  # Extract month
    day = current_datetime[4:6]  # Extract day
    hour = current_datetime[6:8]  # Extract hour
    minute = current_datetime[8:10]  # Extract minute
    second = current_datetime[10:12]  # Extract second

    # Format the string as 'YYYY-MM-DD-HH-MM-SS'
    formatted_datetime = f"{year}-{month}-{day} {hour}:{minute}:{second}"
    return formatted_datetime


def _check_or_create_tuna_folder_tree():
    if not storage_find(DEFAULT_TUNA_FOLDER):
        storage_mkdir(DEFAULT_TUNA_FOLDER)
    if not storage_find(DEFAULT_TUNA_TRAIN_DATASET_PATH):
        storage_mkdir(DEFAULT_TUNA_TRAIN_DATASET_PATH)
    if not storage_find(DEFAULT_TUNA_MODEL_PATH):
        storage_mkdir(DEFAULT_TUNA_MODEL_PATH)


def _get_model_folder_names(train_failed=False, train_succeed=False):
    if train_failed:
        client = APIClient()
        jobs = client.job.list_all()
        running_job_set = set()
        for job in jobs:
            if job.status == LeptonJobState.Running:
                running_job_set.add(job.metadata.name)
    dir_infos = storage_ls(DEFAULT_TUNA_MODEL_PATH, do_print=False)
    model_folder_names = []
    for dir_info in dir_infos:
        if dir_info.type == "dir":
            folder_name = dir_info.name
            job_name = _get_job_name(folder_name)
            if not train_failed and not train_succeed:
                model_folder_names.append(folder_name)
            elif train_failed and not _model_train_completed(folder_name) and job_name not in running_job_set:
                model_folder_names.append(folder_name)
            elif train_succeed and _model_train_completed(train_succeed):
                model_folder_names.append(folder_name)
    return model_folder_names


def _model_train_completed(model_folder_name: str) -> bool:
    dir_infos = storage_ls(DEFAULT_TUNA_MODEL_PATH + '/' + model_folder_name, do_print=False)
    return len(dir_infos) > 1


def _get_model_folder_name(job_name):
    job_name = job_name[len(TUNA_TRAIN_JOB_NAME_PREFIX):]
    model_folder_names = _get_model_folder_names()
    for model_folder_name in model_folder_names:
        if job_name in model_folder_name:
            return model_folder_name


def _get_model_basic_info_from_model_folder_name(job_name=None, model_folder_name=None):
    if job_name:
        model_folder_name = _get_model_folder_name(job_name)
    model_folder_name_arr = model_folder_name.split("-") or ""
    trained_time = model_folder_name_arr[0] if len(model_folder_name_arr) > 0 else "unknown created time"
    model_name = model_folder_name_arr[1] if len(model_folder_name_arr) > 1 else "unknown model name"
    data_name = model_folder_name_arr[2] if len(model_folder_name_arr) > 2 else "unknown data name"
    trained_time = reverse_datetime(trained_time)
    return trained_time, model_name, data_name


@click_group()
def tuna():
    """
    todo
    description here

    data,
        ✅upload
        ✅list
        ✅remove

    train
        ✅create
        ✅list
        ✅stop

    model
        list
        delete
        run

    """
    pass


@tuna.command()
@click.option(
    "--local-path", "-l", type=click.Path(), default=None, help="Local data path."
)
@click.option(
    "--for-test-remote-path",
    type=click.Path(),
    default=None,
    help="Remote folder path.",
)
def upload_data(local_path, for_test_remote_path):
    _check_or_create_tuna_folder_tree()

    if not for_test_remote_path:
        for_test_remote_path = DEFAULT_TUNA_TRAIN_DATASET_PATH

    filename = os.path.basename(local_path)
    remote_path = for_test_remote_path + "/" + filename

    storage_upload(
        local_path,
        remote_path,
    )
    console.print(f"Uploaded Dataset [green]{local_path}[/]")


@tuna.command()
def list_data():
    _check_or_create_tuna_folder_tree()

    storage_ls(DEFAULT_TUNA_TRAIN_DATASET_PATH)


@tuna.command()
@click.option(
    "--data-file-name",
    "-n",
    type=click.Path(),
    required=True,
    help="Data file name like [data.json].",
)
def remove_data(data_file_name):
    _check_or_create_tuna_folder_tree()

    data_file_path = DEFAULT_TUNA_TRAIN_DATASET_PATH + "/" + data_file_name
    if not storage_find(data_file_path):
        console.print(f"[red]Dataset {data_file_name} not found [/]")
        sys.exit(1)

    storage_rm(data_file_path)
    console.print(f"Removed dataset [green]{data_file_name}[/].")


@tuna.command()
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
@click.option("--low-mem-mode", is_flag=True, help="Use low memory mode. Default: Off")
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
        node_groups,
        num_workers,
        max_job_failure_retry,
        resource_shape,
        env,
        # in cmd
        model_path,
        dataset_file_name,
        **kwargs,
        # purpose,
        # num_train_epochs,
        # per_device_train_batch_size,
        # gradient_accumulation_steps,
        # report_wandb,
        # wandb_project,
        # save_steps,
        # learning_rate,
        # warmup_ratio,
        # model_max_length,
        # low_mem_mode,
        # lora,
        # lora_rank,
        # lora_alpha,
        # lora_dropout,
        # medusa,
        # num_medusa_head,
        # early_stop_threshold,
):
    # check data_path

    data_path = DEFAULT_TUNA_TRAIN_DATASET_PATH + "/" + dataset_file_name

    # Build the directory structure
    if not storage_find(data_path):
        console.print(f"[red]{data_path}[/] not found. "
                      f"Please use lep tuna upload-data -l <local_file_path>to upload your data first, "
                      f"and use lep tuna list-data to check your data.")
        sys.exit(1)

    # Generate a name for the model-data job
    output_model_name = _generate_model_folder_name(model_path, dataset_file_name)
    job_name = _get_job_name(output_model_name)
    console.print(f"[green]{job_name}[/]")

    # Generate the output folder
    model_output_dir = DEFAULT_TUNA_MODEL_PATH + "/" + output_model_name
    storage_mkdir(model_output_dir)

    # Construct the command string
    cmd = (
        "run_training"
        f" --model_name_or_path={model_path} --data_path={data_path} --output_dir={model_output_dir}"
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

    console.print(f"[red]{cmd}[/]")

    # Save all parameters to a JSON file and upload to model path
    params = {
        "train_job_name": job_name,
        "model_name": output_model_name,
        "training_resource_shape": resource_shape,
        "node_groups": node_groups,
        "num_workers": num_workers,
        "max_job_failure_retry": max_job_failure_retry,
        "model_path": model_path,
        "dataset_file_name": dataset_file_name,
        "output_dir": model_output_dir,
        **kwargs,
    }

    model_info_file_path, model_info_file_name = _save_params_to_json(
        params, job_name + "_info"
    )

    storage_upload(model_info_file_path, model_output_dir + "/" + model_info_file_name)
    print("model_info_file_path", model_info_file_path)
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
    console.print(f"Model Training Job [green]{job_name}[/] created successfully.")


@tuna.command()
# Todo: move this to list() function
def list_train():
    client = APIClient()
    train_jobs = client.job.list_all()
    logger.trace(f"Model Train Jobs: {train_jobs}")

    table = Table(show_header=True)
    table.add_column("Name")
    table.add_column("Created At")
    table.add_column("State (ready,active,succeeded,failed)")
    table.add_column("Model")
    table.add_column("Data")
    job_name_set = set()
    for job in train_jobs:
        if TUNA_TRAIN_JOB_NAME_PREFIX not in job.metadata.name:
            continue
        if job.status == LeptonJobState.Deleting:
            job_name_set.add(job.metadata.id_)
            continue
        time, model, data = _get_model_basic_info_from_model_folder_name(job_name=job.metadata.id_)
        job_name_set.add(job.metadata.id_)
        status = job.status
        table.add_row(
            job.metadata.name,
            (
                datetime.fromtimestamp(job.metadata.created_at / 1000).strftime(
                    "%Y-%m-%d\n%H:%M:%S"
                )
                if job.metadata.created_at
                else "N/A"
            ),
            f"{status.state} ({status.ready},{status.active},{status.succeeded},{status.failed})",
            model,
            data,
        )

    failed_model_folder_names = _get_model_folder_names(train_failed=True)

    # Simulate a job from the failed model folder
    for failed_model_folder_name in failed_model_folder_names:
        job_name = _get_job_name(failed_model_folder_name)
        # If a failed job exists, we remove duplicates
        if job_name in job_name_set:
            continue
        time, model, data = _get_model_basic_info_from_model_folder_name(model_folder_name=failed_model_folder_name)

        table.add_row(
            job_name,
            (
                time
                if time
                else "N/A"
            ),
            f"{LeptonJobState.Failed} ({0},{0},{0},{1})",
            model,
            data,
        )
    table.title = "Model Train Jobs"
    console.print(table)


@tuna.command()
@click.argument("name")
def delete_train(name):
    client = APIClient()
    jobs = client.job.list_all()
    for job in jobs:
        if job.metadata.name == name:
            client.job.delete(name)
    model_folder_name = _get_model_folder_name(name)
    model_path = DEFAULT_TUNA_MODEL_PATH + '/' + model_folder_name
    if not _model_train_completed(model_folder_name):
        storage_rmdir(model_path, delete_all=True)
    console.print(f"Model Train Job [green]{name}[/] deleted successfully.")


@tuna.command()
def clear_failed_train():
    failed_folder_names = _get_model_folder_names(train_failed=True)
    for failed_folder_name in failed_folder_names:
        model_path = DEFAULT_TUNA_MODEL_PATH + '/' + failed_folder_name
        storage_rmdir(model_path, delete_all=True)


#todo get model info / train info

@tuna.command()
@click.option("--name", "-n", help="model_name")
def run():
    # use deployment create
    pass


@tuna.command()
@click.option("--train-job-name", "-t", help="Model training job name")
@click.option("--model", "-m", help="Trained model name")
def delete():
    pass


def delete_model():
    pass


@tuna.command(name="list")
def list_command():
    """
    Lists all secrets in the current workspace. Note that the secret values are
    always hidden.
    """
    client = APIClient()
    secrets = client.secret.list_all()
    secrets.sort()
    table = Table(title="Secrets", show_lines=True)
    table.add_column("ID")
    table.add_column("Value")
    for secret in secrets:
        table.add_row(secret, "(hidden)")
    console.print(table)


@tuna.command()
@click.option("--name", "-n", help="Secret name")
def remove(name):
    """
    Removes the secret with the given name.
    """
    client = APIClient()
    client.secret.delete(name)
    console.print(f"Secret [green]{name}[/] deleted successfully.")


def add_command(cli_group):
    cli_group.add_command(tuna)
