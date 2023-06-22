from vectordb.api import Collection
from vectordb.client.types import Config
from typing import List, Dict, Any


class Client:
    def __init__(self, Config) -> None:
        pass

    def create_collection(self, name: str, dim: int = 128) -> Collection:
        """
        Creates a collection.

        Args:
            name (str): The Name of the collection.
            dim (int, optional): The dimension of the vector embedding.
            Defaults to 128.

        Returns:
            Collection.
        """
        pass

    def delete_collection(self, name: str) -> None:
        """
        Deletes a collection.

        Args:
            name (str): The name of the collection.
        """
        pass

    def get_collection(self, name: str) -> Collection:
        """
        Gets a collection.

        Args:
            name (str): The name of the collection.

        Returns:
            Collection.
        """
        pass

    def list_collection(self) -> List[Collection]:
        """
        Lists all the collections.

        Returns:
            List[Collection]: A list of collections.
        """
        pass
