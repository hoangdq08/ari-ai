from pydantic import BaseModel
from typing import List

class SearchResultItem(BaseModel):
    title: str
    content: str
    similarity_score: float

class SearchHandbookResponse(BaseModel):
    results: List[SearchResultItem]
