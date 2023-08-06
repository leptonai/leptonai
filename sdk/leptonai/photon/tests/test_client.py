import multiprocessing
import os
import tempfile
import time

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

import responses

from leptonai import Client
from leptonai.photon import Photon, handler
from utils import random_name, find_free_port, photon_run_server


class WeirdlyNamedPhoton(Photon):
    def init(self):
        pass

    @handler("run/with/slashes")
    def run_with_slashes(self):
        return "hello world"

    @handler("run/with-dashes")
    def run_with_dashes(self):
        return "hello world"


def weirdly_named_photon_wrapper(port):
    photon = WeirdlyNamedPhoton()
    photon.launch(port=port)


class TestClient(unittest.TestCase):
    def test_client(self):
        # launch server
        name = random_name()
        proc, port = photon_run_server(name=name, model="hf:gpt2")
        url = f"http://localhost:{port}"

        client = Client(url)
        inputs = "hello world"
        res = client.run(inputs=inputs)
        self.assertTrue(isinstance(res, str))
        self.assertTrue(res.startswith(inputs))
        res = client.run(inputs="hello world", do_sample=True, max_length=10)
        self.assertTrue(isinstance(res, str))
        self.assertTrue(res.startswith(inputs))
        proc.kill()

    def test_client_with_unique_names(self):
        port = find_free_port()
        proc = multiprocessing.Process(
            target=weirdly_named_photon_wrapper, args=(port,)
        )
        proc.start()
        time.sleep(1)
        url = f"http://localhost:{port}"
        client = Client(url)
        # Tests if run_with_slashes and run_with_dashes are both registered
        res = client.run_with_slashes()
        self.assertTrue(res == "hello world")
        res = client.run_with_dashes()
        self.assertTrue(res == "hello world")
        proc.terminate()

    def test_client_with_token(self):
        name = random_name()
        proc, port = photon_run_server(name=name, model="hf:gpt2")
        url = f"http://localhost:{port}"
        inputs = "hello inputs"
        outputs = "hello outputs"
        token = "1234"
        wrong_token = "4321"

        with responses.RequestsMock() as rsps:
            matchers = [
                responses.matchers.header_matcher({"Authorization": f"Bearer {token}"}),
            ]
            rsps.add(
                responses.GET,
                f"{url}/openapi.json",
                json={"paths": {"/run": {"post": {}}}},
                match=matchers,
            )
            rsps.add(
                responses.POST,
                f"{url}/run",
                json={"outputs": outputs},
                match=matchers,
            )

            try:
                client = Client(url)
                res = client.run(inputs=inputs)
            except Exception:
                pass
            else:
                raise Exception("Should not pass with no token")

            try:
                client = Client(url, token=wrong_token)
                res = client.run(inputs=inputs)
            except Exception:
                pass
            else:
                raise Exception("Should not pass with wrong token")

            client = Client(url, token=token)
            res = client.run(inputs=inputs)
            self.assertTrue(res == {"outputs": outputs})

        proc.kill()


if __name__ == "__main__":
    unittest.main()
