import functools
import os
import shlex
import shutil
import subprocess
import tempfile
import time

from celery import shared_task, Task
from django.conf import settings
from django.db import connection
import logtail
from loguru import logger
from pynvml.smi import nvidia_smi

from .models import Dish


class CookTask(Task):
    autoretry_for = (Exception,)
    max_retries = 3

    def before_start(self, task_id, args, kwargs):
        with logtail.context(task={"id": task_id}):
            logger.info(f"Task {task_id} is about to start")
            dish = None
            max_tries = 3
            sleep_time = 1
            for _ in range(max_tries):
                try:
                    dish = Dish.objects.get(task_id=task_id)
                except Dish.DoesNotExist:
                    logger.warning(
                        f"Can not find dish with task_id {task_id}, will retry in"
                        f" {sleep_time}s"
                    )
                    time.sleep(sleep_time)
                else:
                    break
            if dish is None:
                raise RuntimeError(
                    f"Can not find dish with task_id {task_id} (after {max_tries} tries"
                )
            dish.start_run()
            return super().before_start(task_id, args, kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        with logtail.context(task={"id": task_id}):
            logger.info(f"Task {task_id} is done")
            dish = Dish.objects.get(task_id=task_id)
            dish.succeed()
            return super().on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        with logtail.context(task={"id": task_id}):
            logger.error(f"Task {task_id} failed")
            dish = Dish.objects.get(task_id=task_id)
            dish.failed()
            return super().on_failure(exc, task_id, args, kwargs, einfo)


def tuna_task(task_fn):
    @shared_task(base=CookTask, bind=True)
    @functools.wraps(task_fn)
    def wrapped_task_fn(task, *args, **kwargs):
        with logtail.context(task={"id": task.request.id}):
            return task_fn(*args, **kwargs)

    return wrapped_task_fn


@tuna_task
def cook(data_path, model_name_or_path, output_dir):
    logger.info(
        f"Start cooking Tuna Dish with data_path: {data_path}, model_name_or_path:"
        f" {model_name_or_path}, output_dir: {output_dir}"
    )

    if not shutil.which("docker"):
        raise RuntimeError("Docker is not installed")

    image = "us-west1-docker.pkg.dev/lepton-dev/tuna/fastchat:23.04"
    model_path_on_host = os.path.join(
        settings.BASE_DIR, "lepton-llm", model_name_or_path
    )
    if not os.path.exists(model_path_on_host):
        raise RuntimeError(
            f"Requested model {model_name_or_path} does not exist (at path"
            f" {model_path_on_host})"
        )
    model_path_in_container = "/model"
    gcp_key_on_host = os.path.join(settings.BASE_DIR, ".google_application_credentials")
    gcp_key_in_container = "/google_application_credentials"

    nvsmi = nvidia_smi.getInstance()
    gpu0_mem_gb = (
        nvsmi.DeviceQuery("memory.free, memory.total")["gpu"][0]["fb_memory_usage"][
            "total"
        ]
        / 1024
    )
    logger.info(f"GPU0 total memory: {gpu0_mem_gb} GB")
    if gpu0_mem_gb < 30:
        # TODO: test whether A10 can train 7B model (and whether it
        # can do batch size 4)
        per_device_train_batch_size = 4
    elif gpu0_mem_gb < 60:
        per_device_train_batch_size = 8
    else:
        per_device_train_batch_size = 16
    logger.info(f"setting per_device_train_batch_size={per_device_train_batch_size}")

    torch_ext_cache_on_host = os.path.join(
        tempfile.gettempdir(), "cache", "torch_extensions"
    )
    os.makedirs(torch_ext_cache_on_host, exist_ok=True)
    torch_ext_cache_in_container = "/root/.cache/torch_extensions"
    cmd = [
        "docker",
        "run",
        "--rm",
        "--shm-size=1g",
        # TODO: each job use all gpus for now
        "--gpus",
        "all",
        "-v",
        f"{model_path_on_host}:{model_path_in_container}:ro",
        "-v",
        f"{gcp_key_on_host}:{gcp_key_in_container}:ro",
        "-v",
        f"{torch_ext_cache_on_host}:{torch_ext_cache_in_container}",
        "-e",
        f"GOOGLE_APPLICATION_CREDENTIALS={gcp_key_in_container}",
        "-w",
        "/app",
        image,
        "./run_training.sh",
        "--low_mem_mode",
        f"--per_device_train_batch_size={per_device_train_batch_size}",
        f"--model_name_or_path={model_path_in_container}",
        f"--data_path={data_path}",
        f"--output_dir={output_dir}",
    ]
    logger.info(f"Docker command: {shlex.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in proc.stdout:
        logger.opt(raw=True).info(line.decode("utf-8"))
    returncode = proc.wait()
    if returncode:
        raise RuntimeError(
            f"Training failed with return code {returncode} (see logs above)"
        )
    else:
        logger.info("Tuna Dish is ready")

    # closing the connection to force django to reconnect to the db
    connection.close()
