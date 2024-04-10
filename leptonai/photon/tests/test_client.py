from collections.abc import Iterable
import os
import sys
import tempfile
import time

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

import anyio
import httpx
import respx

from leptonai.client import Client, PathTree, local
from leptonai.photon import Photon, handler, StreamingResponse, HTTPException
from utils import random_name, photon_run_local_server, photon_run_local_server_simple


class WeirdlyNamedPhoton(Photon):
    def init(self):
        pass

    @handler("run/with/slashes")
    def run_with_slashes(self):
        return "hello world"

    @handler("run/with-dashes")
    def run_with_dashes(self):
        return "hello world"

    @handler("/")
    def root(self):
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


class PostAndGetSameName(Photon):
    def init(self):
        pass

    @handler(path="run", method="POST")
    def run_post(self) -> str:
        return "post"

    @handler(path="run", method="GET")
    def run_get(self) -> str:
        return "get"


class Throws429(Photon):
    @handler
    def run(self):
        raise HTTPException(status_code=429, detail="Too many requests")


class TestPathTree(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_path_tree_bool(self):
        from leptonai.client import PathTree

        tree = PathTree(name="root", debug_record=[])
        self.assertFalse(tree)

        def temp_func(x):
            return x

        tree._add("foo", temp_func, "get")
        self.assertTrue(tree)


class TestClient(unittest.TestCase):
    tiny_hf_model = "hf:sshleifer/tiny-gpt2@5f91d94"

    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

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

        # Simulate a case where the client failed to connect and there is no automatically
        # generated path tree.
        client._path_cache = PathTree(name="", debug_record=[])
        try:
            client.run(inputs=inputs)
        except AttributeError as e:
            self.assertTrue(
                "It is likely that the client was not initialized, or the client"
                " encountered errors during initialization time."
                in str(e)
            )
        else:
            self.fail(
                "Expected AttributeError from no-path-tree client, but it seems to have"
                " passed."
            )

    def test_client_with_unique_names(self):
        proc, port = photon_run_local_server_simple(WeirdlyNamedPhoton)
        client = Client(local(port=port))
        self.assertTrue(client.healthz())
        # Tests if run_with_slashes and run_with_dashes are both registered
        res = client.run.with_.slashes()
        self.assertTrue(res == "hello world")
        res = client.run.with_dashes()
        self.assertTrue(res == "hello world", client.run())
        res = client()
        self.assertTrue(res == "hello world")

    def test_client_with_post_and_get(self):
        proc, port = photon_run_local_server_simple(PostAndGet)
        client = Client(local(port=port))
        self.assertTrue(client.healthz())
        # Tests if run_post and run_get are both registered
        res = client.run_post(query="post")
        self.assertTrue(res == "hello world (post)")
        res = client.run_get(query="get")
        self.assertTrue(res == "hello world (get)")
        # Tests if we are guarding args - users should use kwargs.
        self.assertRaises(RuntimeError, client.run_post, "post")
        self.assertRaises(RuntimeError, client.run_get, "get")

    def test_client_with_post_and_get_same_name(self):
        proc, port = photon_run_local_server_simple(PostAndGetSameName)
        client = Client(local(port=port))
        self.assertTrue(client.healthz())
        # Tests if run is registered
        res = client.run()
        self.assertEqual(res, "post")
        # Tests if run_post and run_get are both registered
        from leptonai.client import _MultipleEndpointWithDefault

        self.assertIsInstance(
            client.run, _MultipleEndpointWithDefault, client._debug_record
        )
        self.assertEqual(client.run.post(), "post")
        self.assertTrue(client.run.get(), "get")

    def test_client_with_throw_429(self):
        proc, port = photon_run_local_server_simple(Throws429)
        client = Client(local(port=port))
        self.assertTrue(client.healthz())
        self.assertRaises(httpx.HTTPStatusError, client.run)

        proc.kill()

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


class StreamingPhoton(Photon):
    def _simple_generator(self):
        for i in range(10):
            yield bytes(str(i) + ",", "utf-8")

    @handler
    def run(self) -> StreamingResponse:
        return StreamingResponse(self._simple_generator())


class TestStreamingPhotonClient(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_streaming_photon(self):
        proc, port = photon_run_local_server_simple(StreamingPhoton)
        c = Client(local(port=port), stream=True)

        result = c.run()
        self.assertIsInstance(result, Iterable)

        result_list = [r for r in result]
        self.assertIsInstance(result_list, list)
        self.assertEqual(b"".join(result_list), b"0,1,2,3,4,5,6,7,8,9,")

        c = Client(local(port=port), stream=False)

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


class TestNestedPhotonClient(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_nested_photon(self):
        proc, port = photon_run_local_server_simple(ParentPhoton)
        c = Client(local(port=port))

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


class SleepCOD(Photon):
    @Photon.handler(cancel_on_disconnect=0.1)
    def sleep(self, seconds: float) -> str:
        time.sleep(seconds)
        print("sleep done")
        return "ok"

    @Photon.handler(cancel_on_disconnect=0.1)
    async def async_sleep(self, seconds: float) -> str:
        await anyio.sleep(seconds)
        print("async_sleep done")
        return "ok"


class StreamingLongPhoton(Photon):
    def _simple_generator(self):
        for i in range(10):
            time.sleep(0.5)
            print("yielding", i)
            yield bytes(str(i) + ",", "utf-8")

    @handler
    def run(self) -> StreamingResponse:
        return StreamingResponse(self._simple_generator())


class TestClientTimeout(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

        os.environ["LOGURU_LEVEL"] = "TRACE"

    def test_client_timeout(self):
        proc, port = photon_run_local_server_simple(SleepCOD)

        # default: no timeout
        client = Client(local(port=port))
        # We chose 5.1 because 5 is the httpx default - we want to make sure that
        # we have overridden the httpx default.
        self.assertEqual(client.async_sleep(seconds=5.1), "ok")
        self.assertEqual(client.sleep(seconds=5.1), "ok")

        # timeout
        client = Client(local(port=port), timeout=0.5)
        self.assertRaises(httpx.ReadTimeout, client.async_sleep, seconds=6)
        self.assertRaises(httpx.ReadTimeout, client.sleep, seconds=6)

        proc.terminate()
        stdout, stderr = proc.communicate()
        stdout = stdout.decode("utf-8")
        self.assertIn("handle_client_disconnected", stdout, stdout)

    def test_client_timeout_streaming(self):
        proc, port = photon_run_local_server_simple(StreamingLongPhoton)
        # default: no timeout
        client = Client(local(port=port), stream=True)
        result = client.run()
        self.assertIsInstance(result, Iterable)
        result_list = [r for r in result]
        self.assertIsInstance(result_list, list)
        self.assertEqual(b"".join(result_list), b"0,1,2,3,4,5,6,7,8,9,", result_list)
        proc.terminate()
        stdout, stderr = proc.communicate()
        stdout = stdout.decode("utf-8")
        for i in range(10):
            self.assertIn(f"yielding {i}", stdout, stdout)

        # timeout
        proc, port = photon_run_local_server_simple(StreamingLongPhoton)
        client = Client(local(port=port), timeout=0.5)
        with self.assertRaises(httpx.ReadTimeout):
            result = client.run()
            for _ in result:
                pass

        proc.terminate()
        stdout, stderr = proc.communicate()
        stdout = stdout.decode("utf-8")
        self.assertIn("yielding 0", stdout, stdout)
        self.assertNotIn("yielding 9", stdout, stdout)
        # Since the handler actually returned StreamingResponse, the server
        # will not raise ClientDisconnected.
        self.assertIn('"POST /run HTTP/1.1" 200 OK', stdout, stdout)
        self.assertNotIn("handle_client_disconnected", stdout, stdout)


if __name__ == "__main__":
    unittest.main()
