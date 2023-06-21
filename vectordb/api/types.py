
from typing import Dict, List, TypedDict

Embedding = List[float]    
Metadata = Dict[str,str]    

class SearchResponse(TypedDict):
    pass

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