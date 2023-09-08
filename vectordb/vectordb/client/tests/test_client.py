from vectordb.client import Client
import os
import tempfile
import unittest

_COLLECTION_NAME = "test"
_DIM = 512


class TestClient(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        os.environ["DB_DIR"] = self.test_dir.name
        self.cli = Client()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_client_create_collection(self):
        collection = self.cli.create_collection(_COLLECTION_NAME, _DIM)
        self.assertEqual(collection.name, _COLLECTION_NAME)

    def test_client_create_collection_dup(self):
        self.cli.create_collection(_COLLECTION_NAME, _DIM)
        with self.assertRaisesRegex(Exception, f".*{_COLLECTION_NAME}.* already exists"):
            self.cli.create_collection(_COLLECTION_NAME, _DIM)
        
    def test_client_get(self):
        self.cli.create_collection(_COLLECTION_NAME, _DIM)
        collection = self.cli.get_collection(_COLLECTION_NAME)
        self.assertEqual(collection.name, _COLLECTION_NAME)

    def test_client_get_none(self):
        with self.assertRaisesRegex(Exception, f".*{_COLLECTION_NAME}.* not found"):
            self.cli.get_collection(_COLLECTION_NAME)

    def test_client_list(self):
        self.cli.create_collection(_COLLECTION_NAME, _DIM)
        collections = self.cli.list_collections()
        self.assertEqual(len(collections), 1)
        c = collections[0]
        self.assertEqual(c[0], _COLLECTION_NAME)
        self.assertEqual(c[1], _DIM)
    
    def test_client_delete(self):
        self.cli.create_collection(_COLLECTION_NAME, _DIM)
        self.cli.delete_collection(_COLLECTION_NAME)
        collections = self.cli.list_collections()
        self.assertEqual(len(collections), 0)