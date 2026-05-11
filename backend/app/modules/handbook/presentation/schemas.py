from pydantic import BaseModel
from typing import List, Optional

class SearchResultItem(BaseModel):
    id: str
    title: str
    content: str
    category: str
    similarity_score: Optional[float] = None

class SearchHandbookResponse(BaseModel):
    results: List[SearchResultItem]
