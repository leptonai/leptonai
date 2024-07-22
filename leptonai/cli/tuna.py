import json
import os
import random
import re
import string
import sys
import tempfile
from datetime import datetime
from enum import Enum
from typing import Optional, List

import click
from pydantic import BaseModel

from rich.table import Table
from rich.text import Text

from .deployment import deployment_create
from .job import job_create
from .storage import storage_upload, storage_find, storage_mkdir, storage_ls, storage_rm, storage_rmdir, \
    storage_download
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
    TUNA_IMAGE, TUNA_DEPLOYMENT_NAME_PREFIX, LLM_BY_LEPTON_PHOTON_NAME, DEFAULT_RESOURCE_SHAPE,
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
    tuna_model_status: TunaModelState
    deployments: Optional[List[str]] = None
    job_name: Optional[str] = None


def _generate_model_folder_name(model_path, data_filename, is_lora=False, is_medusa=False):
    # Remove all non-alphanumeric characters
    model_filename_clean = model_path.split("/")[-1]
    model_filename_clean = re.sub(r"\W+", "", model_filename_clean).lower()
    data_filename_clean = re.sub(r"\W+", "", data_filename)

    # Get the current date and time
    current_datetime = datetime.now().strftime("%Y%m%d%H%M%S")[2:]

    # Concatenate the strings
    result_string = f"{current_datetime}-{model_filename_clean}-{data_filename_clean}"

    if is_lora:
        result_string += "-lora"
    elif is_medusa:
        result_string += "-medusa"
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

    return temp_file_path


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


def _get_model_deployment_name(model_folder_name):
    client = APIClient()
    deployments = client.deployment.list_all()
    deployment_names_set = {deployment.metadata.name for deployment in deployments}
    base_name = (TUNA_DEPLOYMENT_NAME_PREFIX + model_folder_name)
    counter = 0
    for i in range(0, 999):
        new_name = f"{base_name[:36 - len(str(counter))]}{counter}"
        if new_name not in deployment_names_set:
            return new_name
        counter += 1
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
    return (TUNA_DEPLOYMENT_NAME_PREFIX + model_folder_name)[:32] + random_string


def _get_model_folder_name_chuck_from_deployment_name(deployment_name):
    return deployment_name[32:][len(TUNA_DEPLOYMENT_NAME_PREFIX):]


def build_shortened_model_deployment_map():
    client = APIClient()
    deployments = client.deployment.list_all()
    shortened_model_deployment_map = {}

    for deployment in deployments:
        deployment_name = deployment.metadata.name
        shortened_model_folder_name = deployment_name[32:][len(TUNA_DEPLOYMENT_NAME_PREFIX):]

        if shortened_model_folder_name not in shortened_model_deployment_map:
            shortened_model_deployment_map[shortened_model_folder_name] = [TunaModelState.Running]

        if deployment.status.state is not LeptonDeploymentState.Deleting:
            shortened_model_deployment_map[shortened_model_folder_name].append(
                deployment_name + deployment.status.state)
        if deployment.status.state is LeptonDeploymentState.NotReady:
            shortened_model_deployment_map[0] = TunaModelState.Stopped

    return shortened_model_deployment_map


def _get_model_folder_names():
    dir_infos = storage_ls(DEFAULT_TUNA_MODEL_PATH, do_print=False)
    model_folder_names = []
    for dir_info in dir_infos:
        if dir_info.type == "dir":
            model_folder_names.append(dir_info.name)
    return model_folder_names


def _get_models_map():
    client = APIClient()

    jobs = client.job.list_all()
    running_job_set = set()
    for job in jobs:
        job_status = job.status.state
        if job_status is LeptonJobState.Running or job_status is LeptonJobState.Starting:
            running_job_set.add(job.metadata.name)

    model_deployment_map = build_shortened_model_deployment_map()

    model_folder_names = _get_model_folder_names()
    model_folder_names_map = {}
    for model_folder_name in model_folder_names:
        job_name = _get_job_name(model_folder_name)
        if not _model_train_completed(model_folder_name) and job_name not in running_job_set:
            print(job_name, " not in ", str(running_job_set))
            model_folder_names_map[model_folder_name] = TunaModel(folder_name=model_folder_name,
                                                                  tuna_model_status=TunaModelState.trainFailed)
        elif _model_train_completed(model_folder_name):
            #todo: if not deployed put it ready else put it running
            cur_shorten_model_name = model_folder_name[:32 - len(TUNA_DEPLOYMENT_NAME_PREFIX)]
            if cur_shorten_model_name in model_folder_names_map:
                cur_deployment_info = model_deployment_map[cur_shorten_model_name]
                model_folder_names_map[model_folder_name] = TunaModel(folder_name=model_folder_name,
                                                                      deployments=cur_deployment_info[1:],
                                                                      tuna_model_status=cur_deployment_info[0])
            model_folder_names_map[model_folder_name] = TunaModel(folder_name=model_folder_name,
                                                                  tuna_model_status=TunaModelState.Ready)
        else:
            model_folder_names_map[model_folder_name] = TunaModel(folder_name=model_folder_name,
                                                                  tuna_model_status=TunaModelState.Training)
    return model_folder_names_map


def _model_train_completed(model_folder_name: str) -> bool:
    client = APIClient()
    dir_infos = client.storage.get_dir(DEFAULT_TUNA_MODEL_PATH + '/' + model_folder_name)
    return len(dir_infos) > 1


def _get_model_folder_name(job_name):
    job_name = job_name[len(TUNA_TRAIN_JOB_NAME_PREFIX):]
    models = _get_model_folder_names()
    for model_folder_name in models:
        if job_name in model_folder_name:
            return model_folder_name


def _get_model_basic_info_from_model_folder_name(job_name=None, model_folder_name=None):
    if job_name:
        model_folder_name = _get_model_folder_name(job_name)
    if model_folder_name is None:
        return None, None, None
    model_folder_name_arr = model_folder_name.split("-") or ""
    trained_time = model_folder_name_arr[0] if len(model_folder_name_arr) > 0 else "unknown created time"
    model_name = model_folder_name_arr[1] if len(model_folder_name_arr) > 1 else "unknown model name"
    data_name = model_folder_name_arr[2] if len(model_folder_name_arr) > 2 else "unknown data name"
    lora_or_medusa = model_folder_name_arr[3] if len(model_folder_name_arr) > 3 else None
    trained_time = reverse_datetime(trained_time)
    return trained_time, model_name, data_name, lora_or_medusa


def _get_model_deployments(model_folder_name):
    deployment_name = _get_model_deployment_name(model_folder_name)
    client = APIClient()
    deployments = client.deployment.list_all()
    this_model_deployments = []
    for deployment in deployments:
        if deployment_name in deployment.metadata.name:
            this_model_deployments.append(deployment)
    return this_model_deployments


def _get_info_file_name(model_folder_name):
    return model_folder_name + "_info.json"


def _get_model_output_path(model_folder_name):
    return DEFAULT_TUNA_MODEL_PATH + "/" + model_folder_name


# todo finish this function to get model config from json file
def _get_model_details(model_folder_name):
    info_file_name = _get_info_file_name(model_folder_name)
    info_path = _get_model_output_path(model_folder_name) + '/' + info_file_name
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, info_file_name)

    storage_download(info_path, temp_file_path)

    if not os.path.exists(temp_file_path):
        raise FileNotFoundError(f"The file {temp_file_path} does not exist.")

    with open(temp_file_path, "r") as f:
        params = json.load(f)

    return params


def _get_model_path_from_info(model_folder_name):
    params = _get_model_details(model_folder_name)

    return params.get("model_path") if "model_path" in params else None


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
        ✅list
        ✅delete
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

    model_folder_name = _generate_model_folder_name(model_path, dataset_file_name, kwargs.get("lora"),
                                                    kwargs.get("medusa"))
    job_name = _get_job_name(model_folder_name)
    console.print(f"[green]{job_name}[/]")

    # Generate the output folder
    model_output_path = _get_model_output_path(model_folder_name)
    storage_mkdir(model_output_path)

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
    # todo remove debug print
    console.print(f"[red]{cmd}[/]")

    # Save all parameters to a JSON file and upload to model path
    params = {
        "train_job_name": job_name,
        "model_name": model_folder_name,
        "training_resource_shape": resource_shape,
        "node_groups": node_groups,
        "num_workers": num_workers,
        "max_job_failure_retry": max_job_failure_retry,
        "model_path": model_path,
        "dataset_file_name": dataset_file_name,
        "output_dir": model_output_path,
        **kwargs,
    }

    model_info_file_name = _get_info_file_name(model_folder_name)

    model_info_file_path = _save_params_to_json(
        params, model_info_file_name
    )

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
        f"Model Training Job [green]{job_name}[/] for your model [green]{model_folder_name}[/] created successfully.")


# @tuna.command()
# # Todo: move this to list() function
# def list_train():
#     client = APIClient()
#     train_jobs = client.job.list_all()
#     logger.trace(f"Model Train Jobs: {train_jobs}")
#
#     table = Table(show_header=True)
#     table.add_column("Name")
#     table.add_column("Created At")
#     table.add_column("State (ready,active,succeeded,failed)")
#     table.add_column("Model")
#     table.add_column("Data")
#     job_name_set = set()
#     for job in train_jobs:
#         if TUNA_TRAIN_JOB_NAME_PREFIX not in job.metadata.name:
#             continue
#         if job.status.state == LeptonJobState.Deleting:
#             job_name_set.add(job.metadata.id_)
#             continue
#         time, model, data = _get_model_basic_info_from_model_folder_name(job_name=job.metadata.id_)
#         job_name_set.add(job.metadata.id_)
#         status = job.status.state
#         table.add_row(
#             job.metadata.name,
#             (
#                 datetime.fromtimestamp(job.metadata.created_at / 1000).strftime(
#                     "%Y-%m-%d\n%H:%M:%S"
#                 )
#                 if job.metadata.created_at
#                 else "N/A"
#             ),
#             f"{status.state} ({status.ready},{status.active},{status.succeeded},{status.failed})",
#             model,
#             data,
#         )
#
#     # Simulate a job from the failed model folder
#     for failed_model_folder_name, tuna_model in _get_models_map().items():
#         if tuna_model.tuna_model_status is not TunaModelState.trainFailed:
#             continue
#         job_name = _get_job_name(failed_model_folder_name)
#         # If a failed job exists, we remove duplicates
#         if job_name in job_name_set:
#             continue
#         time, model, data = _get_model_basic_info_from_model_folder_name(model_folder_name=failed_model_folder_name)
#
#         table.add_row(
#             job_name,
#             (
#                 time
#                 if time
#                 else "N/A"
#             ),
#             f"{LeptonJobState.Failed} ({0},{0},{0},{1})",
#             model,
#             data,
#         )
#     table.title = "Model Train Jobs"
#     console.print(table)


# @tuna.command()
# @click.argument("name")
# def delete_train(name):
#     client = APIClient()
#     jobs = client.job.list_all()
#     for job in jobs:
#         if job.metadata.name == name:
#             client.job.delete(name)
#     model_folder_name = _get_model_folder_name(name)
#     model_path = DEFAULT_TUNA_MODEL_PATH + '/' + model_folder_name
#     if not _model_train_completed(model_folder_name):
#         storage_rmdir(model_path, delete_all=True)
#     console.print(f"Model Train Job [green]{name}[/] deleted successfully.")


# todo refine this remove for model have running model
@tuna.command()
@click.argument("model_folder_name")
def remove(model_folder_name):
    client = APIClient()
    jobs = client.job.list_all()
    job_name = _get_job_name(model_folder_name)
    for job in jobs:
        if job.metadata.name == job_name:
            client.job.delete(job_name)

    model_path = DEFAULT_TUNA_MODEL_PATH + '/' + model_folder_name
    if _model_train_completed(model_folder_name):
        console.print(f"[red]The model '{model_folder_name}' is ready and has been trained successfully.[/]")
        user_input = input("Do you want to delete this model? (yes/no): ").strip().lower()
        if user_input == 'no':
            sys.exit(0)
    storage_rmdir(model_path, delete_all=True)
    console.print(f"Model Train Job [green]{model_folder_name}[/] deleted successfully.")


@tuna.command()
def clear_failed_train():
    for folder_name, tuna_model in _get_models_map().items():
        if tuna_model.tuna_model_status is TunaModelState.trainFailed:
            model_path = DEFAULT_TUNA_MODEL_PATH + '/' + folder_name
            storage_rmdir(model_path, delete_all=True)


#todo get model info / train info
#todo change time formate
@tuna.command()
@click.option("--name", "-n", help="--name, also known as the model folder name")
@click.option("--resource-shape", "-rs", default=DEFAULT_RESOURCE_SHAPE, help="Resource shape of the deployment")
@click.option("--node-groups", "-ng", default=None, help="Node groups of the deployment")
@click.option("--hf-transfer",
              is_flag=True,
              default=True,
              help="Set to True for faster uploads and downloads from the Hub using hf_transfer."
              )
@click.option("--tuna-step",
              type=int,
              default=3,
              help=""" in streaming mode, the minimum number of tokens to generate in each new chunk. 
              Smaller numbers send generated results sooner, but may lead to a slightly higher network overhead. 
              Default value set to 3. Unless you are hyper-tuning for benchmarks, you can leave this value as default."""
              )
@click.option("--use-int",
              is_flag=True,
              default=True,
              help=""""Set to true to apply quantization techniques for reducing GPU memory usage. 
              For model size under 7B, or 13B with USE_INT set to true, gpu.a10 is sufficient to run the model, 
              although you might want to use more powerful computation resources.""")
@click.option("--huggingface-token",
              type=str,
              default="HUGGING_FACE_HUB_TOKEN",
              help="""
              Name of your Hugging Face token. By default, it will be 'HUGGING_FACE_HUB_TOKEN'.
              If you haven't created it in your workspace, use:
              lep secret create -n <secret name> -v <secret value>
              """)
@click.option(
    "--mount",
    help=(
            "Persistent storage to be mounted to the deployment, in the format"
            " `STORAGE_PATH:MOUNT_PATH`."
    ),
    multiple=True,
)
def run(
        name,
        resource_shape,
        node_groups,
        hf_transfer,
        tuna_step,
        use_int,
        huggingface_token,
        mount
):
    # use deployment create
    deployment_name = _get_model_deployment_name(name)

    base_model_path = _get_model_path_from_info(name)

    model_output_path = _get_model_output_path(name)

    lora = None
    medusa = None
    if name.endswith("_lora"):
        model_path = "MODEL_PATH=" + base_model_path
        lora = "LORAS="+model_output_path
    elif name.endswith("_medusa"):
        model_path = "MODEL_PATH=" + base_model_path
        medusa = "MEDUSA="+model_output_path
    else:
        model_path = "MODEL_PATH=" + model_output_path

    hf_transfer_num_str = "1" if hf_transfer else "0"
    env = ["HF_HUB_ENABLE_HF_TRANSFER=" + hf_transfer_num_str,
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

    deployment_create(
        deployment_name,
        resource_shape=resource_shape,
        photon_name=LLM_BY_LEPTON_PHOTON_NAME,
        node_groups=node_groups,
        secret=huggingface_token,
        mount=mount
    )

    pass


@tuna.command(name="list")
def list_command():
    """
    Lists all tuna model in this workspace.
    """

    table = Table(show_header=True, header_style="bold magenta", show_lines=True, padding=(0, 1))
    table.add_column("Name")
    table.add_column("Trained At")
    table.add_column("Model")
    table.add_column("Data")
    table.add_column("State (Training, Ready, Running, Stopped, Train Failed)")
    table.add_column("Running Deployments Name")
    table.add_column("Train Job Name")

    for model_folder_name, tuna_model in _get_models_map().items():
        time, model, data, lora_or_medusa = _get_model_basic_info_from_model_folder_name(
            model_folder_name=model_folder_name)
        status = tuna_model.tuna_model_status
        state_style = "green" if status is TunaModelState.Running \
            else "yellow" if status is TunaModelState.Training \
            else "blue" if status is TunaModelState.Ready \
            else "red"

        # todo change the deployment list method, use env to link to the model
        current_deployments = (_get_model_deployments(model_folder_name=model_folder_name)
                               if status is TunaModelState.Running
                               else None)
        if current_deployments:
            cur_deployments_str_list = []
            for deployment in current_deployments:
                cur_deployments_str_list.append(deployment.metadata.name + f"({deployment.status.state})")

        else:
            current_deployments = ""

        table.add_row(
            model_folder_name,
            time if time else "N/A"
            ,
            model,
            data,
            Text(status, style=state_style),
            current_deployments,
            (
                Text(_get_job_name(model_folder_name), style="green")
                if status
                   is TunaModelState.Training
                else "Not Training"
            ),
        )

    table.title = "Tuna Models"
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(tuna)
