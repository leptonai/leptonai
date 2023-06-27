from typing import List
from leptonai import Client
from vectordb.api.types import (
    Embedding,
    Metadata,
    Result,
    GetResponse,
    SearchResponse,
    InsertResponse,
    UpdateResponse,
    DeleteResponse,
)

_ERROR = "error"


def _raise_resp_error(response: dict):
    if response is not None and _ERROR in response:
        raise Exception(response[_ERROR])


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

        Returns:
            UpsertResponse: _description_

        Examples:
            collection.insert(
            keys=["doc1", "doc2"], # must be unique per embedding
            embeddings=[[1,2,3,4,5], [2,2,3,4,5]], #
            metadatas=[{"source": "notion"}, {"source": "google-docs"}],
        """

    def _add(
        self, keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]
    ) -> dict:
        if not _has_same_length(keys, embeddings, metadatas):
            raise Exception(
                "length of keys, embeddings, and metadatas must be the same"
            )
        embs = []
        for idx, e in enumerate(embeddings):
            embs.append(
                {
                    "vector": e,
                    "doc_id": keys[idx],
                    "metatdata": metadatas[idx],
                    "text": "",
                }
            )
        inputs = {"name": self.name, "embeddings": embs}
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
        self._add(keys, embeddings, metadatas)

    def update(
        self, keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]
    ) -> UpdateResponse:
        """
        Given the vector embedding keys, updates their embeddings and metadatas. If the key doesn't exist, then
        an exception will be raised.

        Args:
            keys (List[str]): The vector embedding keys.
            embeddings (List[Embedding]): A list of vector embeddings.
            metadatas (List[Metadata]): The metadatas of the vector embeddings.

        Returns:
            UpdateResponse: Contains update response.
        """

    def delete(self, keys: List[str]) -> DeleteResponse:
        """
        Delete the vector embeddings given their keys.

        Args:
            keys (List[str]): The vector embedding keys.

        Returns:
            DeleteResponse: Contains delete response.
        """
