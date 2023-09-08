from vectordb.client import Client
import numpy as np
import os
import tempfile
import unittest
from math import isclose

_COLLECTION_NAME = "test"
_DIM = 512
_KEY = "doc-id"
_EMBEDDING = np.random.rand(_DIM).tolist()


class TestCollection(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        os.environ["DB_DIR"] = self.test_dir.name
        self.cli = Client()
        self.collection = self.cli.create_collection(_COLLECTION_NAME, _DIM)

    def _compare_embeddings(self, emb1, emb2):
        self.assertEqual(len(emb1), len(emb2))
        for e1, e2 in zip(emb1, emb2):
            # if abs(e1 - e2) < abs_tol, then we consider floats are equal
            self.assertTrue(isclose(e1, e2, abs_tol=1e-05))

    def tearDown(self):
        self.test_dir.cleanup()

    def test_collection_insert(self):
        self.assertIsNone(
            self.collection.insert(keys=[_KEY], embeddings=[_EMBEDDING], metadatas=[{}])
        )
        resp = self.collection.get([_KEY])
        self.assertEqual(len(resp.vectors), 1)
        self.assertEqual(resp.vectors[0].key, _KEY)
        self._compare_embeddings(resp.vectors[0].embedding, _EMBEDDING)
        self.assertEqual(resp.vectors[0].metadata, {})

    def test_collection_insert_again(self):
        self.assertIsNone(
            self.collection.insert(keys=[_KEY], embeddings=[_EMBEDDING], metadatas=[{}])
        )
        with self.assertRaisesRegex(Exception, f".*{_KEY}.* already exist"):
            self.collection.insert(keys=[_KEY], embeddings=[_EMBEDDING], metadatas=[{}])

    def test_collection_delete(self):
        self.collection.insert(keys=[_KEY], embeddings=[_EMBEDDING], metadatas=[{}])
        self.collection.delete(keys=[_KEY])
        resp = self.collection.get(keys=[_KEY])
        self.assertEqual(len(resp.vectors), 0)

    def test_collection_upserts(self):
        self.assertIsNone(
            self.collection.upsert(keys=[_KEY], embeddings=[_EMBEDDING], metadatas=[{}])
        )
        self.assertIsNone(
            self.collection.upsert(
                keys=[_KEY], embeddings=[_EMBEDDING], metadatas=[{"key": "val"}]
            )
        )
        resp = self.collection.get([_KEY])
        self.assertEqual(len(resp.vectors), 1)
        self.assertEqual(resp.vectors[0].key, _KEY)
        self.assertEqual(resp.vectors[0].metadata["key"], "val")

    def test_collection_search(self):
        for i in range(10):
            self.collection.insert(
                keys=[f"{_KEY}_{i}"],
                embeddings=[_EMBEDDING],
                metadatas=[{"key": "val"}],
            )
        resp = self.collection.search(embedding=_EMBEDDING, top_k=1)
        self.assertEqual(len(resp.results), 1)
        self._compare_embeddings(resp.results[0].embedding, _EMBEDDING)
