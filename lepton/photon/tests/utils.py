import atexit
import random
import subprocess
import string
import time


def random_name():
    return "".join(random.choice(string.ascii_lowercase) for _ in range(5))


def photon_run_server(name, model=None, port=8083):
    # TODO: find a better way to test long-running server
    # TODO: implement find free port
    cmd = [
        "lepton",
        "photon",
        "run",
        "-n",
        name,
        "--port",
        str(port),
    ]
    if model is not None:
        cmd += ["-m", model]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    atexit.register(proc.kill)
    for line in proc.stderr:
        line = line.decode("utf-8").lower()
        if "running" in line:
            break
        time.sleep(0.1)
    return proc, port
