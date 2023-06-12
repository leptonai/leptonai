import os
from typing import List, Optional, Dict, Any

from hnsqlite import Collection, Embedding

from leptonai.photon.runner import RunnerPhoton as Runner, handler, HTTPException


class VecDB(Runner):
    requirement_dependency = ["git+https://github.com/bddppq/hnsqlite.git@1f63bc5"]

    def init(self):
        self.db_dir = os.path.dirname(__file__)
        os.makedirs(self.db_dir, exist_ok=True)

        self.collections = {}
        for filename in os.listdir(self.db_dir):
            if not filename.endswith(".sqlite"):
                continue
            collection_name = filename[: -len(".sqlite")]
            sqlite_filename = os.path.join(self.db_dir, filename)
            self.collections[collection_name] = Collection(
                sqlite_filename=sqlite_filename
            )

    def _db_filepath(self, name: str) -> str:
        return os.path.join(self.db_dir, f"{name}.sqlite")

    @handler()
    def create_collection(self, name: str, dim: int = 128):
        if name in self.collections:
            raise HTTPException(
                status_code=400, detail=f"Collection '{name}' already exists"
            )
        sqlite_filename = self._db_filepath(name)
        self.collections[name] = Collection(
            collection_name=name, dimension=dim, sqlite_filename=sqlite_filename
        )

    @handler()
    def remove_collection(self, name: str):
        if name not in self.collections:
            raise HTTPException(
                status_code=400, detail=f"Collection '{name}' not found"
            )
        del self.collections[name]
        sqlite_filename = self._db_filepath(name)
        os.remove(sqlite_filename)

    @handler()
    def list_collections(self) -> List[str]:
        return [(name, col.config.dim) for name, col in self.collections.items()]

    def _get_collection(self, name: str) -> Collection:
        if name not in self.collections:
            raise HTTPException(
                status_code=400, detail=f"Collection '{name}' not found"
            )
        return self.collections[name]

    @handler()
    def add(self, name: str, embeddings: List[Embedding]):
        collection = self._get_collection(name)
        collection.add_embeddings(embeddings)

    @handler()
    def get(self, name: str, doc_ids: List[str]) -> List[Dict[str, Any]]:
        collection = self._get_collection(name)
        return [r.dict() for r in collection.get_embeddings_doc_ids(doc_ids)]

    @handler()
    def search(
        self, name: str, vector: List[float], k: int = 12
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection(name)
        return [r.dict() for r in collection.search(vector, k)]

    @handler()
    def count(self, name: str) -> int:
        collection = self._get_collection(name)
        return collection.count()

    @handler()
    def delete(
        self,
        name: str,
        doc_ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
        delete_all: bool = False,
    ):
        collection = self._get_collection(name)
        collection.delete(doc_ids=doc_ids, filter=filter, delete_all=delete_all)
