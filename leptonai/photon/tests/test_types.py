import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import base64
import os
import sys
import unittest

import requests

from leptonai.client import Client
from leptonai.photon.types import (
    get_file_content,
    to_bool,
)
from leptonai.photon import Photon, handler, StreamingResponse, FileParam

from utils import photon_run_local_server_simple


class StreamingPhoton(Photon):
    def _simple_generator(self):
        for i in range(10):
            yield bytes(str(i) + ",", "utf-8")

    @handler
    def run(self) -> StreamingResponse:
        return StreamingResponse(self._simple_generator())


class TestStreamingPhoton(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def setUp(self) -> None:
        self.proc, self.port = photon_run_local_server_simple(StreamingPhoton)

    def tearDown(self) -> None:
        self.proc.kill()

    def test_streaming_photon_type(self):
        url = f"http://localhost:{self.port}"
        c = Client(url)

        result = c.run()

        self.assertEqual(result, b"0,1,2,3,4,5,6,7,8,9,")


class TestUtil(unittest.TestCase):
    def test_get_file_content(self):
        msg = b"some random message"
        with self.assertWarns(DeprecationWarning):
            file_param = FileParam(msg)
        self.assertEqual(get_file_content(file_param), msg)

        with tempfile.NamedTemporaryFile() as f:
            f.write(msg)
            f.flush()
            self.assertEqual(get_file_content(f.name, allow_local_file=True), msg)

        try:
            content = get_file_content("https://www.google.com/robots.txt")
        except requests.ConnectionError:
            pass
        else:
            self.assertIn(b"User-agent", content)

        encoded = base64.b64encode(msg).decode("utf-8")
        self.assertEqual(get_file_content(encoded), msg)
        self.assertEqual(get_file_content("data:media/txt;base64," + encoded), msg)

        self.assertRaises(TypeError, get_file_content, 1)
        self.assertRaises(TypeError, get_file_content, [])
        self.assertRaises(TypeError, get_file_content, {})
        self.assertRaises(TypeError, get_file_content, [1, 2, 3])

    def test_to_bool(self):
        self.assertTrue(to_bool("True"))
        self.assertTrue(to_bool("true"))
        self.assertTrue(to_bool("t"))
        self.assertTrue(to_bool("T"))
        self.assertTrue(to_bool("1"))
        self.assertTrue(to_bool("yes"))
        self.assertTrue(to_bool("Yes"))
        self.assertTrue(to_bool("y"))
        self.assertTrue(to_bool("Y"))
        self.assertTrue(to_bool("on"))
        self.assertTrue(to_bool("On"))
        self.assertTrue(to_bool("oN"))
        self.assertTrue(to_bool("ON"))

        self.assertFalse(to_bool("False"))
        self.assertFalse(to_bool("false"))
        self.assertFalse(to_bool("f"))
        self.assertFalse(to_bool("F"))
        self.assertFalse(to_bool("0"))
        self.assertFalse(to_bool("no"))
        self.assertFalse(to_bool("No"))
        self.assertFalse(to_bool("n"))
        self.assertFalse(to_bool("N"))
        self.assertFalse(to_bool("off"))
        self.assertFalse(to_bool("Off"))
        self.assertFalse(to_bool("oFf"))
        self.assertFalse(to_bool("OFF"))
        self.assertFalse(to_bool(""))

        self.assertRaises(ValueError, to_bool, "not a boolean value")
        self.assertRaises(ValueError, to_bool, "2")
        self.assertRaises(TypeError, to_bool, 2)
        self.assertRaises(TypeError, to_bool, [])
        self.assertRaises(TypeError, to_bool, {})
        self.assertRaises(TypeError, to_bool, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
