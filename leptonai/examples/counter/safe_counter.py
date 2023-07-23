"""
A simple example of a safe counter that utilizes Lepton storage to keep
states persistent. For the details, please refer to the class comments

To launch a safe counter, you need to have a Lepton storage attached. Run:
    lep photon create -n safe-counter -m safe_counter.py:SafeCounter
    # run locally
    mkdir /mnt/leptonstore
    lep photon run -n safe-counter --local
    # or if you want to run things remote, first push the photon
    lep photon push -n safe-counter
    lep photon run -n safe-counter -dn safe-counter --mount /:/mnt/leptonstore

To test the photon, you can either use the API explorer in the UI, or use
the photon client class in python, e.g.
    from leptonai.client import Client
    # If you are runnnig the photon remotely with workspace id "myworkspace"
    # and deployment name "safe-counter"
    client = Client("myworkspace", "safe-counter")
    # Or if you are running the photon locally at port 8080
    client = Client("http://localhost:8080")
    # Do NOT run the above three commands at the same time! Choose only one.
    print(client.add(x=3))
    print(client.sub(x=5))
etc. You can try to stop and restart safe counter and see that the counter
is persistent.
"""
import errno
import fcntl
import os
import time

from fastapi import HTTPException

from leptonai.photon import Photon


class SafeCounter(Photon):
    """
    An example showing a safe counter using Lepton storage. Note that in actual
    production, you should probably use a locking mechanism better than files,
    such as a database.

    This deployment is stateful, and will be automatically recovered when the
    deployment restarts. It also keeps the counter consistent across replicas.
    It is not "perfectly safe" - if a replica dies before it can write to and
    close a file, an undefined latency may occur.

    To run this example, you need to have a Lepton storage attached to the
    deployment. You can do this by adding the following to the run command:
        --mount [storage path you want to use]:/mnt/leptonstore
    The simplest option for [storage path you want to use] is to use the root
    path of the storage, aka ``--mount /:/mnt/leptonstore``.
    """

    PATH = "/mnt/leptonstore/safe_counter.txt"

    def init(self):
        # checks if the folder containing the file exists
        if not os.path.exists(os.path.dirname(self.PATH)):
            raise RuntimeError(
                "SafeCounter requires a Lepton storage to be attached to the deployment"
                "at /mnt/leptonstore."
            )
        # checks if the file exists
        if not os.path.exists(self.PATH):
            # if not, create the file and write 0 to it. Strictly speaking, this
            # may have a race condition, but it is unlikely to happen in practice
            # and the worst that can happen is that the file is created twice,
            # unless a request comes in right in between two deployments creating
            # the file.
            with open(self.PATH, "w") as file:
                file.write("0")

    @Photon.handler("add")
    def add(self, x: int) -> int:
        # Open the file in read mode
        with open(self.PATH, "r+") as file:
            # Attempt to acquire a non-blocking exclusive lock on the file
            retry = 0
            while retry < 10:
                try:
                    fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except IOError as e:
                    # If the lock cannot be acquired, sleep for a short interval
                    # and try again
                    if e.errno != errno.EAGAIN:
                        raise HTTPException(
                            status_code=500,
                            detail=(
                                "Internal server error: failed to acquire lock on file"
                                " after repeated attempts."
                            ),
                        )
                    retry += 1
                    time.sleep(0.1)

            # Read the current value from the file
            current_value = int(file.read())
            # Increment the value
            new_value = current_value + x
            file.seek(0)
            file.write(str(new_value))
            file.truncate()
            fcntl.flock(file, fcntl.LOCK_UN)
            return new_value

    @Photon.handler("sub")
    def sub(self, x: int) -> int:
        return self.add(-x)
