import base64
from io import BytesIO
import os
import tempfile
import unittest

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Photon, Client
from leptonai.photon.types import File

from utils import random_name, photon_run_local_server


class TestFile(unittest.TestCase):
    def test_file_bytes(self):
        content = b"hello world"
        file_object = File(content)
        self.assertEqual(file_object.get_content(), content)

    def test_file_from_file(self):
        content = b"hello world"
        file_object = File(BytesIO(content))
        self.assertEqual(file_object.get_content(), content)
        ff = File(file_object)
        self.assertEqual(ff.get_content(), content)

    def test_file_str(self):
        # illegal string
        content = "hello world"
        with self.assertRaises(ValueError):
            file_object = File(content)
        # base64 encoded string
        content = "data:application/octet-stream;base64," + base64.b64encode(
            b"hello world"
        ).decode("utf-8")
        file_object = File(content)
        self.assertEqual(file_object.get_content(), b"hello world")
        # url string
        content = "http://example.com"
        file_object = File(content)
        self.assertIn(b"Example Domain", file_object.get_content())

    def test_file_BytesIO(self):
        content = b"hello world"
        file_object = File(BytesIO(content))
        self.assertEqual(file_object.get_content(), content)

    def test_file_local_file(self):
        content = b"hello world"
        with tempfile.NamedTemporaryFile() as f:
            f.write(content)
            f.flush()
            f.seek(0)
            file_object = File(f)
            self.assertEqual(file_object.get_content(), content)

    def test_file_functions(self):
        content = b"hello world"
        file_object = File(content)
        self.assertEqual(file_object.get_content(), content)

        content = b"hello world"
        file_object = File(content)
        self.assertEqual(file_object.get_bytesio().read(), content)

        content = b"hello world"
        file_object = File(content)
        temp_file = file_object.get_temp_file()
        self.assertEqual(temp_file.read(), content)
        with open(temp_file.name, "rb") as f:
            self.assertEqual(f.read(), content)
        temp_file.close()


class EchoFileContent(Photon):
    @Photon.handler
    def run(self, file: File) -> str:
        return file.get_content().decode("utf-8")


class TestFileWithPhotonServer(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_file_with_photon_server(self):
        name = random_name()
        ph = EchoFileContent(name=name)
        path = ph.save()
        proc, port = photon_run_local_server(path=path)
        c = Client(Client.local(port=port))

        # bytes
        content = b"hello world"
        file_object = File(content)
        self.assertEqual(c.run(file=file_object), "hello world")

        # base64 encoded string
        content = "data:application/octet-stream;base64," + base64.b64encode(
            b"hello world"
        ).decode("utf-8")
        file_object = File(content)
        self.assertEqual(c.run(file=file_object), "hello world")

        # url string
        content = "http://example.com"
        file_object = File(content)
        self.assertIn("Example Domain", c.run(file=file_object))

        # BytesIO
        content = b"hello world"
        file_object = File(BytesIO(content))
        self.assertEqual(c.run(file=file_object), "hello world")

        # local file
        content = b"hello world"
        with tempfile.NamedTemporaryFile() as f:
            f.write(content)
            f.flush()
            f.seek(0)
            file_object = File(f)
            self.assertEqual(c.run(file=file_object), "hello world")


if __name__ == "__main__":
    unittest.main()
