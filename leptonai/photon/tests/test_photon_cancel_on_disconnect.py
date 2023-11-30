import anyio
import os
import requests
import tempfile
import time
import unittest

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from fastapi import UploadFile

from leptonai import Photon

from utils import random_name, photon_run_local_server


class CODRawArgs(Photon):
    """
    This class will not work because it uses use_raw_args=True and
    cancel_on_disconnect, which is not supported.
    """

    @Photon.handler(use_raw_args=True, cancel_on_disconnect=0.1)
    def filename(self, file: UploadFile) -> str:
        return file.filename  # type: ignore


class COD(Photon):
    @Photon.handler(cancel_on_disconnect=0.1)
    def sleep(self, seconds: int) -> str:
        time.sleep(seconds)
        print("sleep done")
        return "ok"

    @Photon.handler(cancel_on_disconnect=0.1)
    async def async_sleep(self, seconds: int) -> str:
        await anyio.sleep(seconds)
        print("async_sleep done")
        return "ok"


class TestPhotonCOD(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])
        os.environ["LOGURU_LEVEL"] = "TRACE"

    def test_cannot_do_cod_and_raw_args(self):
        p = CODRawArgs()
        with self.assertRaises(ValueError):
            p.launch()

    def test_cancel_on_disconnect(self):
        name = random_name()
        ph = COD(name=name)
        path = ph.save()

        proc, port = photon_run_local_server(path=path)

        url = f"http://127.0.0.1:{port}/"

        resp = requests.post(url + "sleep", json={"seconds": 1})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), "ok", resp.json)

        resp = requests.post(url + "async_sleep", json={"seconds": 1})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), "ok", resp.json)

        # Test that the server returns 503 when the client disconnects.
        with self.assertRaises(requests.exceptions.ReadTimeout):
            resp = requests.post(url + "sleep", json={"seconds": 3}, timeout=1)
        proc.terminate()
        stdout, stderr = proc.communicate()
        stdout = stdout.decode("utf-8")
        self.assertIn("handle_client_disconnected", stdout, stdout)
        self.assertIn(
            'raise HTTPException(status_code=503, detail="Client disconnected.")',
            stdout,
            stdout,
        )
        # Note: when calling "sleep", although the server will do cancellation, the actual sync
        # sleep is not cancelled. So we will see "sleep done" in stdout.
        self.assertIn("sleep done", stdout, stdout)

        # Restart the server, and retries async_sleep
        proc, port = photon_run_local_server(path=path)
        url = f"http://127.0.0.1:{port}/"
        # Test that the server returns 503 when the client disconnects.
        with self.assertRaises(requests.exceptions.ReadTimeout):
            resp = requests.post(url + "async_sleep", json={"seconds": 3}, timeout=1)
        proc.terminate()
        stdout, stderr = proc.communicate()
        stdout = stdout.decode("utf-8")
        self.assertIn("handle_client_disconnected", stdout, stdout)
        self.assertIn(
            'raise HTTPException(status_code=503, detail="Client disconnected.")',
            stdout,
            stdout,
        )
        # Note: when calling "async_sleep" with cancellation, async sleep is cancelled.
        # So we will not see "async_sleep done" in stdout.
        self.assertNotIn("async_sleep done", stdout, stdout)


if __name__ == "__main__":
    unittest.main()
