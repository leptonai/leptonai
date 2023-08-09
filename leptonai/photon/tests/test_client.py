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
from utils import random_name, find_free_port, photon_run_local_server


class WeirdlyNamedPhoton(Photon):
    def init(self):
        pass

    @handler("run/with/slashes")
    def run_with_slashes(self):
        return "hello world"

    @handler("run/with-dashes")
    def run_with_dashes(self):
        return "hello world"


class PostAndGet(Photon):
    def init(self):
        pass

    @handler("run_post", method="POST")
    def run_post(self, query: str):
        return f"hello world ({query})"

    @handler("run_get", method="GET")
    def run_get(self, query: str):
        return f"hello world ({query})"


def weirdly_named_photon_wrapper(port):
    photon = WeirdlyNamedPhoton()
    photon.launch(port=port)


def post_and_get_wrapper(port):
    photon = PostAndGet()
    photon.launch(port=port)


class TestClient(unittest.TestCase):
    def test_client(self):
        # launch server
        name = random_name()
        proc, port = photon_run_local_server(name=name, model="hf:gpt2")
        url = f"http://localhost:{port}"

        client = Client(url)
        inputs = "hello world"
        res = client.run(inputs=inputs)
        self.assertTrue(client.healthz())
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
        self.assertTrue(client.healthz())
        # Tests if run_with_slashes and run_with_dashes are both registered
        res = client.run_with_slashes()
        self.assertTrue(res == "hello world")
        res = client.run_with_dashes()
        self.assertTrue(res == "hello world")
        proc.terminate()

    def test_client_with_post_and_get(self):
        port = find_free_port()
        proc = multiprocessing.Process(target=post_and_get_wrapper, args=(port,))
        proc.start()
        time.sleep(1)
        url = f"http://localhost:{port}"
        client = Client(url)
        self.assertTrue(client.healthz())
        # Tests if run_post and run_get are both registered
        res = client.run_post(query="post")
        self.assertTrue(res == "hello world (post)")
        res = client.run_get(query="get")
        self.assertTrue(res == "hello world (get)")
        # Tests if we are guarding args - users should use kwargs.
        self.assertRaises(RuntimeError, client.run_post, "post")
        self.assertRaises(RuntimeError, client.run_get, "get")
        proc.terminate()

    def test_client_with_token(self):
        name = random_name()
        proc, port = photon_run_local_server(name=name, model="hf:gpt2")
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
            rsps.add(
                responses.GET,
                f"{url}/healthz",
                json={},  # doesn't matter
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
            self.assertTrue(client.healthz())
            res = client.run(inputs=inputs)
            self.assertTrue(res == {"outputs": outputs})

        proc.kill()


if __name__ == "__main__":
    unittest.main()
