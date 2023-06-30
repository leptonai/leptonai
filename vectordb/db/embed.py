from vectordb.db.vecdb import VecDB
from vectordb.api.types import Embedding
from hnsqlite import Embedding as HEmbedding
from functools import wraps
from typing import Any, Callable, Dict, List, Tuple
from leptonai.photon import HTTPException
import time


def handle_exception(func: Callable):
    @wraps(func)
    def handle(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException as err:
            return {"error": err.detail}
        except Exception as err:
            return {"error": err}

    return handle


def _to_hembeddings(embeddings: List[dict]) -> List[HEmbedding]:
    embeds = []
    for e in embeddings:
        embeds.append(
            HEmbedding(
                doc_id=e["doc_id"],
                text=e["text"],
                vector=e["vector"],
                metadata=e["metadata"],
                created_at=time.time(),
            )
        )
    return embeds


class VecDBEmbed(VecDB):
    @handle_exception
    def create_collection(self, *args, **kwargs) -> None:
        super().create_collection(*args, **kwargs)

    @handle_exception
    def remove_collection(self, *args, **kwargs) -> None:
        super().remove_collection(*args, **kwargs)

    @handle_exception
    def list_collections(self, *args, **kwargs) -> List[Tuple[Any, Any]]:
        return super().list_collections(*args, **kwargs)

    @handle_exception
    def update(self, name: str, embeddings: List[dict]) -> None:
        super().update(name=name, embeddings=_to_hembeddings(embeddings))

    @handle_exception
    def upsert(self, name: str, embeddings: List[dict]) -> None:
        super().upsert(name=name, embeddings=_to_hembeddings(embeddings))

    @handle_exception
    def add(self, name: str, embeddings: List[Embedding]) -> None:
        super().add(name=name, embeddings=_to_hembeddings(embeddings))

    @handle_exception
    def get(self, *args, **kwargs) -> List[Dict[str, Any]]:
        return super().get(*args, **kwargs)

    @handle_exception
    def search(self, *args, **kwargs) -> List[Dict[str, Any]]:
        return super().search(*args, **kwargs)

    @handle_exception
    def delete(self, *args, **kwargs) -> None:
        super().delete(*args, **kwargs)
