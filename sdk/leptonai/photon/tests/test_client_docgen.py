# flask8: noqa
import multiprocessing
import os
import tempfile
import time
from typing import Optional, List, Tuple
import unittest


# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Client
from leptonai.photon import Photon, handler
from utils import find_free_port


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


def photon_with_different_docs_wrapper(port):
    photon = PhotonWithDifferentDocs()
    photon.launch(port=port)


class TestClientDocgen(unittest.TestCase):
    def test_client_with_unique_names(self):
        port = find_free_port()
        proc = multiprocessing.Process(
            target=photon_with_different_docs_wrapper, args=(port,)
        )
        proc.start()
        time.sleep(1)
        url = f"http://localhost:{port}"
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

        proc.terminate()


if __name__ == "__main__":
    unittest.main()
