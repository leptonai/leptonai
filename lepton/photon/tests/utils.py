import atexit
import os
import random
import subprocess
import string
import time


def random_name():
    return "".join(random.choice(string.ascii_lowercase) for _ in range(5))


def photon_run_server(name=None, path=None, model=None, port=8083):
    # TODO: find a better way to test long-running server
    # TODO: implement find free port

    if name is None and path is None:
        raise ValueError("Either name or path must be specified")
    if name is not None and path is not None:
        raise ValueError("Only one of name or path can be specified")
    cmd = [
        "lepton",
        "photon",
        "run",
    ]
    if name:
        cmd += ["-n", name]
    if path:
        cmd += ["-f", path]
    cmd += ["--port", str(port)]
    if model is not None:
        cmd += ["-m", model]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    atexit.register(proc.kill)
    lines = []
    for line in proc.stderr:
        line = line.decode("utf-8")
        lines.append(line)
        if "running" in line.lower():
            break
        time.sleep(0.1)
    else:
        # "running" never showed up in the output, which means the
        # server failed to start
        proc.kill()
        raise RuntimeError(f"Photon server failed to start:{os.linesep}{os.linesep.join(lines)}")
    return proc, port
