import os
import requests
import tempfile
import unittest

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Photon
from leptonai.photon import PNGResponse, StreamingResponse

from utils import random_name, photon_run_local_server


# Sometimes, a user might would like to return a specific response type but
# still return None in some cases, and we should support that by returning 204.
class EmptyReturn(Photon):
    @Photon.handler
    def foo(self) -> PNGResponse:
        return None

    @staticmethod
    def iterator():
        content = ["Hello", " ", "World"]
        for c in content:
            yield c

    @Photon.handler
    def bar(self, return_empty: bool = False) -> StreamingResponse:
        if return_empty:
            return None
        else:
            return StreamingResponse(EmptyReturn.iterator(), media_type="text/plain")


class TestPhotonEmpty(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_empty_return(self):
        ph = EmptyReturn(name=random_name())
        path = ph.save()
        proc, port = photon_run_local_server(path=path)

        url = f"http://127.0.0.1:{port}/"
        resp = requests.post(url + "foo")
        self.assertEqual(resp.status_code, 204)
        resp = requests.post(url + "bar", json={"return_empty": True})
        self.assertEqual(resp.status_code, 204)
        resp = requests.post(url + "bar", json={"return_empty": False})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"Hello World")


if __name__ == "__main__":
    unittest.main()
