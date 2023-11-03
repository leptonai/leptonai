import os
import requests
import tempfile
from typing import List
import unittest

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from fastapi import UploadFile

from leptonai import Photon

from utils import random_name, photon_run_local_server


class UploadFile(Photon):
    @Photon.handler(use_raw_args=True)
    def filename(self, file: UploadFile) -> str:
        return file.filename

    @Photon.handler(use_raw_args=True)
    def multiplefiles(self, files: List[UploadFile]) -> List[str]:
        return [f.filename for f in files]


class TestPhotonRawArgs(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_upload_file(self):
        name = random_name()
        ph = UploadFile(name=name)
        path = ph.save()

        proc, port = photon_run_local_server(path=path)

        # TODO: refactor client code to upload files.
        url = f"http://127.0.0.1:{port}/"
        with open(__file__, "rb") as f:
            resp = requests.post(url + "filename", files={"file": f})
            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertEqual(resp.json(), os.path.basename(__file__), resp.json)

            resp = requests.post(url + "multiplefiles", files=[("files", f)] * 3)
            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertEqual(resp.json(), [os.path.basename(__file__)] * 3, resp.json)


if __name__ == "__main__":
    unittest.main()
