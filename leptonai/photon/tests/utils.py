import asyncio
import atexit
import copy
import functools
import os
import random
import requests
import subprocess
import string
import time
from typing import Type

from loguru import logger

from leptonai.photon import Photon
from leptonai.util import asyncfy, find_available_port


def random_name():
    return "".join(random.choice(string.ascii_lowercase) for _ in range(5))


def photon_run_local_server(name=None, path=None, model=None, port=None, env=None):
    if name is None and path is None:
        raise ValueError("Either name or path must be specified")
    if name is not None and path is not None:
        raise ValueError("Only one of name or path can be specified")
    if path is not None and model is not None:
        raise ValueError("model cannot be specified when path is specified")
    if port is None:
        port = find_available_port()
    cmd = [
        "lep",
        "photon",
        "runlocal",
    ]
    if name:
        cmd += ["-n", name]
    if path:
        cmd += ["-f", path]
    cmd += ["--port", str(port)]
    if model is not None:
        cmd += ["-m", model]

    if env is not None:
        env = {**copy.deepcopy(os.environ), **env}

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    atexit.register(proc.kill)

    max_wait = 120
    start_time = time.time()
    while True:
        if proc.poll() is not None:
            stdout = proc.stdout.read().decode("utf-8")
            raise RuntimeError(
                f"Photon server exited with code {proc.returncode}\n{stdout}"
            )

        # ping port to see if it's ready
        if time.time() - start_time > max_wait:
            proc.kill()
            stdout = proc.stdout.read().decode("utf-8")
            raise RuntimeError(
                f"Photon server failed to start on port {port} in"
                f" {max_wait} seconds\n{stdout}"
            )

        try:
            requests.get(f"http://localhost:{port}/healthz")
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)
        else:
            logger.info(f"Photon server started on port {port}")
            return proc, port


def photon_run_local_server_simple(photon_class: Type[Photon], env=None):
    ph = photon_class(name=random_name())
    path = ph.save()
    proc, port = photon_run_local_server(path=path, env=env)
    return proc, port


def sub_test(params_list):
    """poor man's parameterized test"""

    def decorator(f):
        @functools.wraps(f)
        def wrapped(self):
            for params in params_list:
                with self.subTest(params=params):
                    f(self, *params)

        return wrapped

    return decorator


def async_test(f):
    """decorator to run a test asynchronously"""

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(asyncfy(f)(*args, **kwargs))

    return wrapped


def skip_if_macos(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if os.uname().sysname == "Darwin":
            return
        return f(*args, **kwargs)

    return wrapped
