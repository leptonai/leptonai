import multiprocessing
import os
import tempfile
import time
import unittest

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Photon
from leptonai.client import Client, local

from leptonai.config import set_local_deployment_token
from leptonai.util import find_available_port

from utils import random_name, photon_run_local_server


class MyPhoton(Photon):
    @Photon.handler
    def foo(self) -> str:
        return "bar"

    @Photon.handler(method="GET")
    def foo_get(self) -> str:
        return "bar"

    @Photon.handler
    def hello(self, name: str) -> str:
        return f"Hello {name}"


class TestPhotonAuth(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_auth(self):
        os.environ["LEPTON_LOCAL_DEPLOYMENT_TOKEN"] = "test_token"
        ph = MyPhoton(name=random_name())
        path = ph.save()
        proc, port = photon_run_local_server(path=path)

        with self.assertRaises(ConnectionError):
            c = Client(local(port=port))
        c = Client(local(port=port), token="test_token")
        self.assertEqual(c.foo(), "bar")
        self.assertEqual(c.foo_get(), "bar")
        self.assertEqual(c.hello(name="world"), "Hello world")

    def test_auth_with_set(self):
        os.environ["LEPTON_LOCAL_DEPLOYMENT_TOKEN"] = ""
        set_local_deployment_token("test_token2")

        def subprocess_launch_wrapper(port):
            set_local_deployment_token("test_token2")
            photon = MyPhoton()
            photon.launch(port=port)

        port = find_available_port()
        proc = multiprocessing.Process(target=subprocess_launch_wrapper, args=(port,))
        proc.start()
        time.sleep(1)

        with self.assertRaises(ConnectionError):
            c = Client(local(port=port))

        c = Client(local(port=port), token="test_token2")
        self.assertEqual(c.foo(), "bar")
        self.assertEqual(c.foo_get(), "bar")
        self.assertEqual(c.hello(name="world"), "Hello world")

        proc.kill()
        set_local_deployment_token("")


if __name__ == "__main__":
    unittest.main()
