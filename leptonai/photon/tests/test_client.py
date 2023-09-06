from collections.abc import Iterable
import multiprocessing
import os
import tempfile
import time

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

import httpx
import respx

from leptonai import Client
from leptonai.photon import Photon, handler, StreamingResponse
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
    tiny_hf_model = "hf:sshleifer/tiny-gpt2@5f91d94"

    def test_client(self):
        # launch server
        name = random_name()
        proc, port = photon_run_local_server(name=name, model=self.tiny_hf_model)
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
        res = client.run.with_.slashes()
        self.assertTrue(res == "hello world")
        res = client.run.with_dashes()
        self.assertTrue(res == "hello world", client.run())
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
        proc, port = photon_run_local_server(name=name, model=self.tiny_hf_model)
        url = f"http://localhost:{port}"
        inputs = "hello inputs"
        outputs = "hello outputs"
        token = "1234"
        wrong_token = "4321"

        def check_token(request):
            if request.headers.get("Authorization") != f"Bearer {token}":
                return httpx.Response(401, json={"detail": "Unauthorized"})
            return httpx.Response(200, json={"outputs": outputs})

        with respx.mock:
            respx.get(f"{url}/openapi.json").respond(
                200, json={"paths": {"/run": {"post": {}}}}
            )
            respx.get(f"{url}/healthz").respond(200, json={})
            respx.post(f"{url}/run").mock(side_effect=check_token)

            client = Client(url)
            self.assertRaisesRegex(
                Exception,
                "Unauthorized",
                client.run,
                inputs=inputs,
                msg="Should not pass with no token",
            )

            client = Client(url, token=wrong_token)
            self.assertRaisesRegex(
                Exception,
                "Unauthorized",
                client.run,
                inputs=inputs,
                msg="Should not pass with wrong token",
            )

            client = Client(url, token=token)
            self.assertTrue(client.healthz())
            res = client.run(inputs=inputs)
            self.assertTrue(res == {"outputs": outputs})

        proc.kill()


class StreamingPhoton(Photon):
    def _simple_generator(self):
        for i in range(10):
            yield bytes(str(i) + ",", "utf-8")

    @handler
    def run(self) -> StreamingResponse:
        return StreamingResponse(self._simple_generator())


def streaming_photon_wrapper(port):
    photon = StreamingPhoton()
    photon.launch(port=port)


class TestStreamingPhotonClient(unittest.TestCase):
    def setUp(self) -> None:
        self.port = find_free_port()
        self.proc = multiprocessing.Process(
            target=streaming_photon_wrapper, args=(self.port,)
        )
        self.proc.start()
        time.sleep(2)

    def tearDown(self) -> None:
        self.proc.terminate()

    def test_streaming_client(self):
        url = f"http://localhost:{self.port}"
        c = Client(url, stream=True)

        result = c.run()
        self.assertIsInstance(result, Iterable)

        result_list = [r for r in result]
        self.assertIsInstance(result_list, list)
        self.assertEqual(b"".join(result_list), b"0,1,2,3,4,5,6,7,8,9,")

    def test_non_streaming_client(self):
        url = f"http://localhost:{self.port}"
        c = Client(url, stream=False)

        result = c.run()
        self.assertEqual(result, b"0,1,2,3,4,5,6,7,8,9,")


class ChildPhoton(Photon):
    @Photon.handler()
    def greet(self) -> str:
        return "hello from child"


class ParentPhoton(Photon):
    @Photon.handler()
    def greet(self) -> str:
        return "hello from parent"

    @Photon.handler(mount=True)
    def child(self):
        return ChildPhoton()


def parent_photon_wrapper(port):
    photon = ParentPhoton()
    photon.launch(port=port)


class TestNestedPhotonClient(unittest.TestCase):
    def setUp(self) -> None:
        self.port = find_free_port()
        self.proc = multiprocessing.Process(
            target=parent_photon_wrapper, args=(self.port,)
        )
        self.proc.start()
        time.sleep(2)

    def tearDown(self) -> None:
        self.proc.terminate()

    def test_nested_photon(self):
        url = f"http://localhost:{self.port}"
        c = Client(url)

        result = c.greet()
        self.assertEqual(result, "hello from parent")

        child_docstring = c.child()
        self.assertIn(
            "A wrapper for leptonai Client that contains the following paths:\n- greet",
            child_docstring,
            child_docstring,
        )

        result = c.child.greet()
        self.assertEqual(result, "hello from child")


if __name__ == "__main__":
    unittest.main()
