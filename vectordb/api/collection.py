from typing import List
from leptonai import Client
from vectordb.api.types import (
    Embedding,
    Metadata,
    Result,
    Vector,
    GetResponse,
    SearchResponse,
    InsertResponse,
)

_ERROR = "error"


def _raise_resp_error(response: dict):
    if response is not None and _ERROR in response:
        raise Exception(response[_ERROR])


def _to_embs(keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]):
    embs = []
    for k, e, m in zip(keys, embeddings, metadatas):
        embs.append(
            {
                "vector": e,
                "doc_id": k,
                "metatdata": m,
                "text": "",
            }
        )
    return embs


def _has_same_length(
    keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]
) -> bool:
    return len(keys) == len(embeddings) == len(metadatas)


class Collection:
    def __init__(self, name: str, client: Client) -> None:
        self.name = name
        self.client = client

    def search(
        self, embedding: Embedding, top_k: int = 10, with_metadata: bool = True
    ) -> SearchResponse:
        """
        Finds the top k vector embeddings.

        Args:
            embedding (Embedding): The vector embedding.
            top_k (int, optional): Specifies the number of results . Defaults to 10.
            with_metadata (bool, optional): When specified, embedding's metadata is also returned. Defaults to True.

        Returns:
            SearchResponse: Contains top k search results.
        """
        # TODO(fanminshi) implement metadata filter on the server side.
        inputs = {"name": self.name, "vector": embedding, "k": top_k}
        resp = self.client.search(**inputs)
        _raise_resp_error(resp)
        results = []
        for v in resp:
            results.append(
                Result(
                    embedding=v["vector"],
                    metadata=v["metadata"],
                    distance=v["distance"],
                    key=v["doc_id"],
                )
            )
        return SearchResponse(results)

    def get(self, keys: List[str]) -> GetResponse:
        """
        Retrieves a list of vector embeddings given their keys.

        Args:
            keys (List[str]): The vector embedding keys

        Returns:
            GetResponse: Contains vector embeddings.
        """
        inputs = {"name": self.name, "doc_ids": keys}
        resp = self.client.get(**inputs)
        vectors = []
        for v in resp:
            vectors.append(
                Vector(
                    embedding=v["vector"],
                    metadata=v["metadata"],
                    key=v["doc_id"],
                )
            )
        return GetResponse(vectors=vectors)

    def upsert(
        self, keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]
    ) -> None:
        """
        Given the vector embedding keys, updates their embeddings and metadatas. If the key doesn't exist,
        then the operation will insert the embedding and metadata.

        Args:
            keys (List[str]): The vector embedding keys.
            embeddings (List[Embedding]): A list of vector embeddings.
            metadatas (List[Metadata]): The metadatas of the vector embeddings.
        """
        if not _has_same_length(keys, embeddings, metadatas):
            raise Exception(
                "length of keys, embeddings, and metadatas must be the same"
            )
        inputs = {
            "name": self.name,
            "embeddings": _to_embs(
                keys=keys, embeddings=embeddings, metadatas=metadatas
            ),
        }
        resp = self.client.upsert(**inputs)
        _raise_resp_error(resp)

    def _add(
        self, keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]
    ) -> dict:
        if not _has_same_length(keys, embeddings, metadatas):
            raise Exception(
                "length of keys, embeddings, and metadatas must be the same"
            )
        inputs = {
            "name": self.name,
            "embeddings": _to_embs(
                keys=keys, embeddings=embeddings, metadatas=metadatas
            ),
        }
        return self.client.add(**inputs)

    def insert(
        self, keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]
    ) -> InsertResponse:
        """
        Given the vector embedding keys, inserts their embeddings and metadatas. If the key already exists, then
        an exception will be raised.

        Args:
            keys (List[str]): The vector embedding keys.
            embeddings (List[Embedding]): A list of vector embeddings.
            metadatas (List[Metadata]): The metadatas of the vector embeddings.

        Returns:
            InsertResponse: Contains insert response.
        """
        resp = self._add(keys, embeddings, metadatas)
        _raise_resp_error(resp)

    def update(
        self, keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]
    ) -> None:
        """
        Given the vector embedding keys, updates their embeddings and metadatas. If any of the keys don't exist, then
        no updates will be made.

        Args:
            keys (List[str]): The vector embedding keys.
            embeddings (List[Embedding]): A list of vector embeddings.
            metadatas (List[Metadata]): The metadatas of the vector embeddings.

        Returns:
            UpdateResponse: Contains update response.
        """
        if not _has_same_length(keys, embeddings, metadatas):
            raise Exception(
                "length of keys, embeddings, and metadatas must be the same"
            )
        inputs = {
            "name": self.name,
            "embeddings": _to_embs(
                keys=keys, embeddings=embeddings, metadatas=metadatas
            ),
        }
        resp = self.client.update(**inputs)
        _raise_resp_error(resp)

    def delete(self, keys: List[str]) -> None:
        """
        Delete the vector embeddings given their keys.

        Args:
            keys (List[str]): The vector embedding keys.

        Returns:
            DeleteResponse: Contains delete response.
        """
        inputs = {"name": self.name, "doc_ids": keys}
        resp = self.client.delete(**inputs)
        _raise_resp_error(resp)
