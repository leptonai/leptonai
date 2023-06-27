from typing import Dict, List, TypedDict
from dataclasses import dataclass


Embedding = List[float]
Metadata = Dict[str, str]


@dataclass
class Result:
    embedding: Embedding
    metadata: Metadata
    key: str
    distance: float


@dataclass
class SearchResponse:
    results: List[Result]


class GetResponse(TypedDict):
    pass


class UpsertResponse(TypedDict):
    pass


class InsertResponse(TypedDict):
    pass


class UpdateResponse(TypedDict):
    pass


class DeleteResponse(TypedDict):
    pass
