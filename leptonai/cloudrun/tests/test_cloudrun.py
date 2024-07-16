import os
import sys
import time
import unittest

from leptonai.cloudrun import Remote
from leptonai.photon import Photon
from leptonai import api


class MyPhoton(Photon):
    @Photon.handler
    def foo(self) -> str:
        return "hello world!"


try:
    conn = api.v0.workspace.current_connection()
except RuntimeError:
    conn = None


class TestInline(unittest.TestCase):
    @unittest.skipIf(conn is None, "No connection to Lepton AI cloud")
    def test_inline(self):
        remote_run = Remote(MyPhoton())
        self.assertEqual(remote_run.foo(), "hello world!")
        # run again
        remote_run = Remote(MyPhoton())
        self.assertEqual(remote_run.foo(), "hello world!")
        # run with class
        remote_run = Remote(MyPhoton)
        self.assertEqual(remote_run.foo(), "hello world!")
        remote_run = Remote("hf:gpt2")
        ret = remote_run.run(inputs="Once upon a time,")
        self.assertTrue(isinstance(ret, str))
        self.assertTrue(len(ret) > 0)
        self.assertTrue(ret.startswith("Once upon a time,"))
        del remote_run

    @unittest.skipIf(conn is None, "No connection to Lepton AI cloud")
    def test_empty_photon(self):
        remote_run = Remote(Photon)
        self.assertTrue(remote_run.healthz())
        del remote_run

    @unittest.skipIf(conn is None, "No connection to Lepton AI cloud")
    def test_dependency_photon(self):
        sys.path.append(os.path.dirname(__file__))
        from test_submodule.foo import Foo

        sys.path.remove(os.path.dirname(__file__))
        # Without the local file, Foo() will raise an error.
        self.assertRaises(RuntimeError, Remote, Foo())

    @unittest.skipIf(conn is None, "No connection to Lepton AI cloud")
    def test_timeout(self):
        remote_run = Remote(MyPhoton(), no_traffic_timeout=60)
        self.assertTrue(remote_run.healthz())
        self.assertEqual(remote_run.foo(), "hello world!")

        # The tiemout check is done with +- 30 second margin, so we wait for
        # a sufficiently long time.
        time.sleep(90)
        # Test if it is actually shut down
        deployment_id = remote_run.deployment_id
        self.assertIsNotNone(deployment_id)
        dep_info = api.v0.deployment.get_deployment(
            api.v0.workspace.current_connection(), str(deployment_id)
        )
        self.assertIsInstance(dep_info, dict)
        self.assertEqual(dep_info["status"]["state"], "Not Ready")

        remote_run.restart()
        self.assertTrue(remote_run.healthz())
        self.assertEqual(remote_run.foo(), "hello world!")
        remote_run.close()
        self.assertEqual(remote_run.client, None)
        del remote_run


if __name__ == "__main__":
    unittest.main()
