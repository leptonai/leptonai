import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

from celery import shared_task, Task
from django.conf import settings
from loguru import logger

from .models import Dish


class CookTask(Task):
    autoretry_for = (Exception,)
    max_retries = 3

    def before_start(self, task_id, args, kwargs):
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
        logger.info(f"Task {task_id} is done")
        dish = Dish.objects.get(task_id=task_id)
        dish.succeed()
        return super().on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed")
        dish = Dish.objects.get(task_id=task_id)
        dish.failed()
        return super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(base=CookTask)
def cook(data_path, model_name_or_path, output_dir):
    logger.info(
        f"Start cooking Tuna Dish with data_path: {data_path}, model_name_or_path:"
        f" {model_name_or_path}, output_dir: {output_dir}"
    )

    if not shutil.which("docker"):
        raise RuntimeError("Docker is not installed")

    image = "us-west1-docker.pkg.dev/lepton-dev/tuna/fastchat:23.03"
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
    per_device_train_batch_size = 16
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
    log_lines = []
    for line in proc.stdout:
        line = line.decode("utf-8")
        sys.stdout.write(line)
        log_lines.append(line)
    returncode = proc.wait()
    if returncode:
        logger.error(f"returncode={returncode}")
        raise RuntimeError(
            "Failed to run"
            f" docker:\ncmd:\n{shlex.join(cmd)}\nreturncode:\n{returncode}\nlog:\n{''.join(log_lines)}"
        )
    else:
        logger.info("Tuna Dish is ready")
