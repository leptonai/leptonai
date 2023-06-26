from leptonai import Client as LepClient
from vectordb.api.collection import Collection
from vectordb.client.types import Config
from typing import List, Tuple

_ERROR = "error"


def _raise_resp_error(response: dict):
    if response is not None and _ERROR in response:
        raise Exception(response[_ERROR])


class Client:
    def __init__(self, config: Config) -> None:
        self.client = LepClient(config.url)

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
        inputs = {"name": name, "dim": dim}
        resp = self.client.create_collection(**inputs)
        _raise_resp_error(resp)
        return Collection(name=name, client=self.client)

    def delete_collection(self, name: str) -> None:
        """
        Deletes a collection.

        Args:
            name (str): The name of the collection.
        """
        inputs = {"name": name}
        resp = self.client.remove_collection(**inputs)
        _raise_resp_error(resp)

    def get_collection(self, name: str) -> Collection:
        """
        Gets a collection.

        Args:
            name (str): The name of the collection.

        Returns:
            Collection.
        """
        resp = self.list_collections()
        for c in resp:
            if c[0] is name:
                return Collection(name=name, client=self.client)
        raise Exception(f"collection {name} not found")

    def list_collections(self) -> List[Tuple[str, int]]:
        """_summary_

        Raises:
            Exception: error while retrieving the list of collection

        Returns:
            List[Tuple[str, int]]: collection list in term of
            (name, dimension) tuples.
        """
        resp = self.client.list_collections()
        if resp is None:
            raise Exception("unable to list collections")
        _raise_resp_error(resp)
        return resp
