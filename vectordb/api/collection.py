from typing import List
from lepton_vectordb.client import Client
from lepton_vectordb.api.types import (
    Embedding, Metadata, GetResponse, SearchResponse, UpsertResponse, InsertResponse, UpdateResponse, DeleteResponse)

class Collection():
    def __init__(self, name: str, client: Client) -> None:
        pass

    def search(self,
               embedding: Embedding,
               top_k, int = 10,
               with_metadata: bool = True) -> SearchResponse:
        """
        Finds the top k vector embeddings.

        Args:
            embedding (Embedding): The vector embedding. 
            top_k (int, optional): Specifies the number of results . Defaults to 10.
            with_metadata (bool, optional): When specified, embedding's metadata is also returned. Defaults to True.

        Returns:
            SearchResponse: Contains top k search results.
        """
        pass

    def get(self, keys: List[str]) -> GetResponse:
        """
        Retrieves a list of vector embeddings given their keys.

        Args:
            keys (List[str]): The vector embedding keys 

        Returns:
            GetResponse: Contains vector embeddings.
        """
        pass

    def upsert(self, keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]) -> UpsertResponse:
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
        pass

    def insert(self,  keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]) -> InsertResponse:
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
        pass

    def update(self, keys: List[str], embeddings: List[Embedding], metadatas: List[Metadata]) -> UpdateResponse:
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
        pass

    def delete(self, keys: List[str]) -> DeleteResponse:
        """
        Delete the vector embeddings given their keys.

        Args:
            keys (List[str]): The vector embedding keys.

        Returns:
            DeleteResponse: Contains delete response.
        """
        pass