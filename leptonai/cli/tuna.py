import sys

import click

from rich.table import Table

from .storage import storage_upload, storage_find
from .util import (
    console,
    click_group,
)
from ..api.v1.client import APIClient


@click_group()
def tuna():
    """
    todo
    description here

    data,
        upload
        list

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


@tuna.command()
def upload(local_path, remote_path):
    storage_upload(
        local_path,
        remote_path,
    )


@tuna.command()
@click.option("--model-path", type=click.Path(), default=None, help="Model path.")
@click.option("--data-path", type=click.Path(), default=None, help="Data path.")
@click.option("--output-dir", type=click.Path(), default=None, help="Output directory.")
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
    model_path,
    data_path,
    output_dir,
    purpose,
    num_train_epochs,
    per_device_train_batch_size,
    gradient_accumulation_steps,
    report_wandb,
    wandb_project,
    save_steps,
    learning_rate,
    warmup_ratio,
    model_max_length,
    low_mem_mode,
    lora,
    lora_rank,
    lora_alpha,
    lora_dropout,
    medusa,
    num_medusa_head,
    early_stop_threshold,
):
    # check data_path
    if not storage_find(data_path):
        console.print(f"[red]{data_path}[/] not found")
        sys.exit(1)



    pass


@tuna.command()
def list():
    pass


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
