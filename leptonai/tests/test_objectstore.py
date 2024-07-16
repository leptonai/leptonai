from io import StringIO, BytesIO
import random
import requests
import string
import tempfile

from leptonai import PrivateObjectStore, PublicObjectStore
from leptonai.api.v0 import workspace as workspace_api
from leptonai.photon.types.file import File

import unittest


def random_name():
    return "".join(random.choice(string.ascii_lowercase) for _ in range(8))


_content = """The quick brown fox jumps over the lazy dog."""
_test_file_name = random_name() + ".txt"


@unittest.skipIf(
    workspace_api.WorkspaceInfoLocalRecord.get_current_workspace_id() is None,
    "No login info. Skipping test.",
)
class TestObjectStore(unittest.TestCase):
    def _test_file_like(self, client, f):
        # put a file.
        url = client.put(_test_file_name, f)
        files = client.list_objects()
        self.assertIn(_test_file_name, [f["key"] for f in files])

        # get the content of the returned url, and compare it with the original content.
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, _content.encode("utf-8"))

        # get the file from the key
        with client.get(_test_file_name) as downloaded_object:
            self.assertEqual(downloaded_object.read(), _content.encode("utf-8"))
        # delete the file.
        client.delete(_test_file_name)

    def _test_oss_client(self, client):
        client.delete(_test_file_name)
        files = client.list_objects()
        self.assertNotIn(_test_file_name, [f["key"] for f in files])
        # get with non-existing key raises an error.
        with self.assertRaises(RuntimeError):
            client.get(_test_file_name)
        # but get with the returl url will find 404.
        url = client.get(_test_file_name, return_url=True)
        response = requests.get(url)
        self.assertEqual(response.status_code, 404)

        with tempfile.TemporaryFile() as f:
            f.write(_content.encode("utf-8"))
            f.flush()
            f.seek(0)
            self._test_file_like(client, f)
        with tempfile.NamedTemporaryFile() as f:
            f.write(_content.encode("utf-8"))
            f.flush()
            f.seek(0)
            # passing in a name should also work.
            self._test_file_like(client, f.name)
        with BytesIO(_content.encode("utf-8")) as f:
            self._test_file_like(client, f)
        with StringIO(_content) as f:
            self._test_file_like(client, f)

        f = File(_content.encode("utf-8"))
        self._test_file_like(client, f)

    def test_oss(self):
        self._test_oss_client(PrivateObjectStore())
        self._test_oss_client(PublicObjectStore())


if __name__ == "__main__":
    unittest.main()
