"""
A simple example to show a minimal example of a photon: a counter that keeps
states in memory. Note that this is for illustrative purpose only - read the
fine prints in the class comments.

To launch a counter, run:
    lep photon create -n counter -m counter.py:Counter
    # run locally
    lep photon run -n counter
    # or if you want to run things remote, first push the photon
    lep photon push -n counter
    lep photon run -n counter -dn counter

To test the photon, you can either use the API explorer in the UI, or use
the photon client class in python, e.g.
    from leptonai.client import Client
    # If you are runnnig the photon remotely with workspace id "myworkspace"
    # and deployment name "counter"
    client = Client("myworkspace", "counter")
    # Or if you are running the photon locally at port 8080
    client = Client("http://localhost:8080")
    # Do NOT run the above two commands at the same time! Choose only one.
    print(client.add(x=3))
    print(client.sub(x=5))
"""

from leptonai.photon import Photon


class Counter(Photon):
    """
    A simple example showing a counter. The counter is initialized to 0 and
    can be incremented or decremented by calling the ``add`` or ``sub`` methods.

    Note that this is not a safe counter: when there are multiple replicas,
    every replica will have its own counter. Also, when the deployment restarts,
    the counter will be reset to 0. It is an example to show how not to assume
    that the deployments are automatically stateful. Remember, deployments are
    stateless by default unless you use a stateful storage like Lepton storage,
    or a database.

    An example to implement a minimal stateful counter is shown in the
    separate safe_counter example.
    """

    def init(self):
        self.counter = 0

    @Photon.handler("add")
    def add(self, x: int) -> int:
        self.counter += x
        return self.counter

    @Photon.handler("sub")
    def sub(self, x: int) -> int:
        return self.add(-x)
