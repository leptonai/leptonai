import os
import re
import sys
from datetime import datetime

import click
from loguru import logger

from rich.table import Table

from .storage import storage_upload, storage_find, storage_mkdir, storage_ls, storage_rm
from .util import (
    console,
    click_group,
)
from ..api.v1.client import APIClient
from ..config import DEFAULT_TUNA_TRAIN_DATASET_PATH, DEFAULT_TUNA_FOLDER, DEFAULT_TUNA_MODEL_PATH, \
    TUNA_TRAIN_JOB_NAME_PREFIX


def _generate_train_job_name(model_path, data_filename):
    # Remove all non-alphanumeric characters
    model_filename_clean = re.sub(r'\W+', '', model_path)
    data_filename_clean = re.sub(r'\W+', '', data_filename)

    # Get the current date and time
    current_datetime = datetime.now().strftime('%Y%m%d-%H-%M')

    # Concatenate the strings
    result_string = f"{model_filename_clean}-{data_filename_clean}-{current_datetime}"

    return result_string


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
        create
        list
        stop

    model
        list
        delete
        run

    """
    pass


def check_or_create_tuna_folder_tree():
    if not storage_find(DEFAULT_TUNA_FOLDER):
        storage_mkdir(DEFAULT_TUNA_FOLDER)
    if not storage_find(DEFAULT_TUNA_TRAIN_DATASET_PATH):
        storage_mkdir(DEFAULT_TUNA_TRAIN_DATASET_PATH)
    if not storage_find(DEFAULT_TUNA_MODEL_PATH):
        storage_mkdir(DEFAULT_TUNA_MODEL_PATH)


@tuna.command()
@click.option("--local-path", '-lp', type=click.Path(), default=None, help="Local data path.")
@click.option("--for-test-remote-path", type=click.Path(), default=None, help="Remote folder path.")
def upload_data(local_path, for_test_remote_path):
    check_or_create_tuna_folder_tree()

    if not for_test_remote_path:
        for_test_remote_path = DEFAULT_TUNA_TRAIN_DATASET_PATH

    filename = os.path.basename(local_path)
    remote_path = for_test_remote_path + '/' + filename

    storage_upload(
        local_path,
        remote_path,
    )
    console.print(f"Uploaded Dataset [green]{local_path}[/]")


@tuna.command()
def list_data():
    check_or_create_tuna_folder_tree()

    storage_ls(DEFAULT_TUNA_TRAIN_DATASET_PATH)


@tuna.command()
@click.option("--data-file-name", "-n", type=click.Path(), required=True, help="Data file name like [data.json].")
def remove_data(data_file_name):
    check_or_create_tuna_folder_tree()

    data_file_path = DEFAULT_TUNA_TRAIN_DATASET_PATH + '/' + data_file_name
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
@click.option("--model-path", type=click.Path(), default=None, help="Model path.", required=True)
@click.option("--dataset-file-name", '-dn', type=click.Path(), default=None, help="Data path.", required=True)
@click.option("--output-dir", type=click.Path(), default=None, help="Output directory.", required=True)
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
        resource_shape,
        node_groups,
        model_path,
        dataset_file_name,
        output_dir,
        **kwargs
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

    data_path = DEFAULT_TUNA_TRAIN_DATASET_PATH + '/' + dataset_file_name

    if not storage_find(data_path):
        console.print(f"[red]{data_path}[/] not found")
        sys.exit(1)

    cmd = f"python --version --model-path {model_path} --data-path {data_path} --output-dir {output_dir}"
    for key, value in kwargs.items():
        if value is not None:
            option = f"--{key.replace('_', '-')}"
            if isinstance(value, bool) and value:
                cmd += f" {option}"
            elif isinstance(value, str):
                cmd += f" {option} \"{value}\""
            else:
                cmd += f" {option} {value}"

    console.print(f"[red]{cmd}[/]")

    job_name = TUNA_TRAIN_JOB_NAME_PREFIX + '-' + _generate_train_job_name(model_path, dataset_file_name)

    console.print(f"[green]{job_name}[/]")

    mount = [f"{DEFAULT_TUNA_FOLDER}:{DEFAULT_TUNA_FOLDER}"]


    # job_create()


@tuna.command()
def list_train():
    client = APIClient()
    train_jobs = client.job.list_all()
    logger.trace(f"Model Train Jobs: {train_jobs}")

    table = Table(show_header=True)
    table.add_column("Name")
    table.add_column("Created At")
    table.add_column("State (ready,active,succeeded,failed)")
    for job in train_jobs:
        if TUNA_TRAIN_JOB_NAME_PREFIX not in job.metadata.id_:
            continue
        status = job.status
        table.add_row(
            job.metadata.id_,
            (
                datetime.fromtimestamp(job.metadata.created_at / 1000).strftime(
                    "%Y-%m-%d\n%H:%M:%S"
                )
                if job.metadata.created_at
                else "N/A"
            ),
            f"{status.state} ({status.ready},{status.active},{status.succeeded},{status.failed})",
        )
    table.title = "Model Train Jobs"
    console.print(table)

@tuna.command()
@click.option("--name", "-n", help="Job name")
def remove_train(name):
    client = APIClient()
    client.job.delete(name)
    console.print(f"Model Train Job [green]{name}[/] deleted successfully.")
@tuna.command()
def run():
    pass


@tuna.command()
def delete():
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
