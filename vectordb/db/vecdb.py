import os
from typing import List, Optional, Dict, Any, Tuple

from hnsqlite import Collection, Embedding

from leptonai.photon import Photon, HTTPException


class VecDB(Photon):
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

    @Photon.handler()
    def create_collection(self, name: str, dim: int = 128):
        if name in self.collections:
            raise HTTPException(
                status_code=400, detail=f"Collection '{name}' already exists"
            )
        sqlite_filename = self._db_filepath(name)
        self.collections[name] = Collection(
            collection_name=name, dimension=dim, sqlite_filename=sqlite_filename
        )

    @Photon.handler()
    def remove_collection(self, name: str):
        if name not in self.collections:
            raise HTTPException(
                status_code=400, detail=f"Collection '{name}' not found"
            )
        del self.collections[name]
        sqlite_filename = self._db_filepath(name)
        os.remove(sqlite_filename)

    @Photon.handler()
    def list_collections(self) -> List[Tuple[Any, Any]]:
        return [(name, col.config.dim) for name, col in self.collections.items()]

    def _get_collection(self, name: str) -> Collection:
        if name not in self.collections:
            raise HTTPException(
                status_code=400, detail=f"Collection '{name}' not found"
            )
        return self.collections[name]

    @Photon.handler()
    def update(self, name: str, embeddings: List[Embedding]):
        collection = self._get_collection(name)
        to_update = [e.doc_id for e in embeddings]
        existing_doc_ids = [
            r.doc_id for r in collection.get_embeddings_doc_ids(to_update)
        ]
        if len(existing_doc_ids) != len(to_update):
            raise HTTPException(
                status_code=400,
                detail=f"'{set(to_update) - set(existing_doc_ids)}' do not exist",
            )
        collection.delete(doc_ids=to_update)
        collection.add_embeddings(embeddings)

    @Photon.handler()
    def upsert(self, name: str, embeddings: List[Embedding]):
        collection = self._get_collection(name)
        to_upsert = [e.doc_id for e in embeddings]
        # TODO(fanminshi): handle update without deleting entries.
        collection.delete(doc_ids=to_upsert)
        collection.add_embeddings(embeddings)

    @Photon.handler()
    def add(self, name: str, embeddings: List[Embedding]):
        collection = self._get_collection(name)
        to_add = [e.doc_id for e in embeddings]
        existing_doc_ids = [r.doc_id for r in collection.get_embeddings_doc_ids(to_add)]
        if existing_doc_ids:
            raise HTTPException(
                status_code=400, detail=f"'{existing_doc_ids}' already exist"
            )
        collection.add_embeddings(embeddings)

    @Photon.handler()
    def get(self, name: str, doc_ids: List[str]) -> List[Dict[str, Any]]:
        collection = self._get_collection(name)
        return [r.dict() for r in collection.get_embeddings_doc_ids(doc_ids)]

    @Photon.handler()
    def search(
        self, name: str, vector: List[float], k: int = 12
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection(name)
        return [r.dict() for r in collection.search(vector, k)]

    @Photon.handler()
    def count(self, name: str) -> int:
        collection = self._get_collection(name)
        return collection.count()

    @Photon.handler()
    def delete(
        self,
        name: str,
        doc_ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
        delete_all: bool = False,
    ):
        collection = self._get_collection(name)
        collection.delete(doc_ids=doc_ids, filter=filter, delete_all=delete_all)
