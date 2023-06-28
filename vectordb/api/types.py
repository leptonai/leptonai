from typing import Dict, List, TypedDict
from dataclasses import dataclass


Embedding = List[float]
Metadata = Dict[str, str]


@dataclass
class Vector:
    embedding: Embedding
    metadata: Metadata
    key: str


@dataclass
class Result(Vector):
    distance: float


@dataclass
class SearchResponse:
    results: List[Result]


@dataclass
class GetResponse:
    vectors: List[Vector]


class UpsertResponse(TypedDict):
    pass


class InsertResponse(TypedDict):
    pass


class UpdateResponse(TypedDict):
    pass


class DeleteResponse(TypedDict):
    pass
