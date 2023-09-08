import os
import sys
import unittest

from leptonai.cloudrun import Remote
from leptonai.photon import Photon
from leptonai import api


class MyPhoton(Photon):
    @Photon.handler
    def foo(self) -> str:
        return "hello world!"


try:
    conn = api.workspace.current_connection()
except RuntimeError:
    conn = None


class TestInline(unittest.TestCase):
    def tearDown(self) -> None:
        # Ensure that the Remote objects are properly cleaned.
        import gc

        gc.collect()

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


if __name__ == "__main__":
    unittest.main()
