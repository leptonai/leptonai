# flask8: noqa
import os
import sys
import tempfile
from typing import Optional, List, Tuple
import unittest

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Client
from leptonai.photon import Photon, handler
from utils import photon_run_local_server_simple


class PhotonWithDifferentDocs(Photon):
    def init(self):
        pass

    @handler
    def run(self):
        return "hello world"

    @handler("run2")
    def run2(self):
        """
        This is the docstring for run2.
        """
        return "hello world"

    @handler("run3", example={"query": "hello"})
    def run3(self, query):
        return f"hello world {query}"

    @handler("run4")
    def run4(self, query: str):
        return f"hello world {query}"

    @handler("run5")
    def run5(self, query: str, query2: int):
        return f"hello world {query} {query2}"

    @handler("run6")
    def run6(self, query: str) -> str:
        return f"hello world {query}"

    @handler("run7")
    def run7(self, query: str, query2: Optional[str] = None) -> str:
        return f"hello world {query} {query2}"

    @handler("run8")
    def run8(self, query: str, query2: str = "test") -> str:
        return f"hello world {query} {query2}"

    @handler("run9")
    def run9(self, query: List[int], query2: Tuple[str, int]) -> str:
        return f"hello world {query} {query2}"

    @handler("run10")
    def run10(self) -> Tuple[str, str, int]:
        return ("hello", "world", 1)

    @handler(method="GET")
    def getrun(self):
        return "hello world"

    @handler(method="GET")
    def getrun2(self):
        """
        This is the docstring for getrun2.
        """
        return "hello world"

    @handler(method="GET", example={"query": "hello"})
    def getrun3(self, query):
        return f"hello world {query}"

    @handler(method="GET")
    def getrun4(self, query: str):
        return f"hello world {query}"

    @handler(method="GET")
    def getrun5(self, query: str, query2: int):
        return f"hello world {query} {query2}"

    @handler(method="GET")
    def getrun6(self, query: str) -> str:
        return f"hello world {query}"

    @handler(method="GET")
    def getrun7(self, query: str, query2: Optional[str] = None) -> str:
        return f"hello world {query} {query2}"

    @handler(method="GET")
    def getrun8(self, query: str, query2: str = "test") -> str:
        return f"hello world {query} {query2}"

    @handler(method="GET")
    def getrun9(self, query: List[int], query2: Tuple[str, int]) -> str:
        return f"hello world {query} {query2}"

    @handler(method="GET")
    def getrun10(self) -> Tuple[str, str, int]:
        return ("hello", "world", 1)


class TestClientDocgen(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def setUp(self) -> None:
        self.proc, self.port = photon_run_local_server_simple(PhotonWithDifferentDocs)

    def tearDown(self) -> None:
        self.proc.kill()

    def test_client_with_unique_names(self):
        url = f"http://localhost:{self.port}"
        client = Client(url)
        self.assertTrue(client.healthz())
        # Test that the client has the correct documents
        self.assertIn("Run", client.run.__doc__)
        self.assertIn("Input Schema: None", client.run.__doc__)
        self.assertIn("Output Schema:\n  output: Any", client.run.__doc__)

        self.assertNotIn("Run2", client.run2.__doc__)
        self.assertIn("This is the docstring for run2.", client.run2.__doc__)
        self.assertIn("Input Schema: None", client.run.__doc__)
        self.assertIn("Output Schema:\n  output: Any", client.run.__doc__)

        self.assertIn("Run3", client.run3.__doc__)
        self.assertIn("query*: Any", client.run3.__doc__)
        self.assertIn("Example input:", client.run3.__doc__)
        self.assertIn("query: hello", client.run3.__doc__)

        self.assertIn("Run4", client.run4.__doc__)
        self.assertIn("query*: str", client.run4.__doc__)

        self.assertIn("Run5", client.run5.__doc__)
        self.assertIn("query*: str", client.run5.__doc__)
        self.assertIn("query2*: int", client.run5.__doc__)

        self.assertIn("Run6", client.run6.__doc__)
        self.assertIn("query*: str", client.run6.__doc__)
        self.assertIn("Output Schema:\n  output: str", client.run6.__doc__)

        self.assertIn("Run7", client.run7.__doc__)
        self.assertIn("query*: str", client.run7.__doc__)
        # different fastapi versions different typestr for Optional[str], sometimes it's str, sometimes it's (str | None)
        self.assertTrue(
            "query2: str" in client.run7.__doc__
            or "query2: (str | None)" in client.run7.__doc__,
            client.run7.__doc__,
        )
        self.assertIn("Output Schema:\n  output: str", client.run7.__doc__)

        self.assertIn("Run8", client.run8.__doc__)
        self.assertIn("query*: str", client.run8.__doc__)
        self.assertIn("query2: str (default: test)", client.run8.__doc__)
        self.assertIn("Output Schema:\n  output: str", client.run8.__doc__)

        self.assertIn("Run9", client.run9.__doc__)
        self.assertIn("query*: array[int]", client.run9.__doc__)
        self.assertTrue(
            "query2*: array[Any]" in client.run9.__doc__
            or "query2*: array[str, int]" in client.run9.__doc__,
            client.run9.__doc__,
        )

        self.assertIn("Run10", client.run10.__doc__)
        self.assertTrue(
            "output: array[Any]" in client.run10.__doc__
            or "output: array[str, str, int]" in client.run10.__doc__,
            client.run10.__doc__,
        )

        try:
            client.run5("hello")
        except RuntimeError as e:
            error_str = str(e)
            self.assertIn(
                "Did you mean the following?\n    run5(\n        query='hello',\n    )",
                error_str,
            )

        try:
            client.run5("hello", 1)
        except RuntimeError as e:
            error_str = str(e)
            self.assertIn(
                "Did you mean the following?\n    run5(\n        query='hello',\n  "
                "      query2=1,\n    )",
                error_str,
            )

    def test_client_with_unique_names_get(self):
        url = f"http://localhost:{self.port}"
        client = Client(url)
        self.assertTrue(client.healthz())
        # Test that the client has the correct documents
        self.assertIn("Getrun", client.getrun.__doc__)
        self.assertIn("Input Schema: None", client.getrun.__doc__)
        self.assertIn("Output Schema:\n  output: Any", client.getrun.__doc__)

        self.assertNotIn("Getrun2", client.getrun2.__doc__)
        self.assertIn("This is the docstring for getrun2.", client.getrun2.__doc__)
        self.assertIn("Input Schema: None", client.getrun.__doc__)
        self.assertIn("Output Schema:\n  output: Any", client.getrun.__doc__)

        self.assertIn("Getrun3", client.getrun3.__doc__)
        self.assertIn("query*: Any", client.getrun3.__doc__)
        # Example not supported by get method yet.
        self.assertNotIn("Example input:", client.getrun3.__doc__)
        self.assertNotIn("query: hello", client.getrun3.__doc__)

        self.assertIn("Getrun4", client.getrun4.__doc__)
        self.assertIn("query*: str", client.getrun4.__doc__)

        self.assertIn("Getrun5", client.getrun5.__doc__)
        self.assertIn("query*: str", client.getrun5.__doc__)
        self.assertIn("query2*: int", client.getrun5.__doc__)

        self.assertIn("Getrun6", client.getrun6.__doc__)
        self.assertIn("query*: str", client.getrun6.__doc__)
        self.assertIn("Output Schema:\n  output: str", client.getrun6.__doc__)

        self.assertIn("Getrun7", client.getrun7.__doc__)
        self.assertIn("query*: str", client.getrun7.__doc__)
        # different fastapi versions different typestr for Optional[str], sometimes it's str, sometimes it's (str | None)
        self.assertTrue(
            "query2: str" in client.getrun7.__doc__
            or "query2: (str | None)" in client.getrun7.__doc__,
            client.getrun7.__doc__,
        )
        self.assertIn("Output Schema:\n  output: str", client.getrun7.__doc__)

        self.assertIn("Getrun8", client.getrun8.__doc__)
        self.assertIn("query*: str", client.getrun8.__doc__)
        self.assertIn("query2: str (default: test)", client.getrun8.__doc__)
        self.assertIn("Output Schema:\n  output: str", client.getrun8.__doc__)

        self.assertIn("Getrun9", client.getrun9.__doc__)
        self.assertIn("query*: array[int]", client.getrun9.__doc__)
        self.assertTrue(
            "query2*: array[Any]" in client.getrun9.__doc__
            or "query2*: array[str, int]" in client.getrun9.__doc__,
            client.getrun9.__doc__,
        )

        self.assertIn("Getrun10", client.getrun10.__doc__)
        self.assertTrue(
            "output: array[Any]" in client.getrun10.__doc__
            or "output: array[str, str, int]" in client.getrun10.__doc__,
            client.getrun10.__doc__,
        )

        try:
            client.getrun5("hello")
        except RuntimeError as e:
            error_str = str(e)
            self.assertIn(
                "Photon methods do not support positional arguments. If your client is"
                " named `c`, Use `help(c.getrun5)` to see the function signature.",
                error_str,
            )

        try:
            client.getrun5("hello", 1)
        except RuntimeError as e:
            error_str = str(e)
            self.assertIn(
                "Photon methods do not support positional arguments. If your client is"
                " named `c`, Use `help(c.getrun5)` to see the function signature.",
                error_str,
            )


if __name__ == "__main__":
    unittest.main()
