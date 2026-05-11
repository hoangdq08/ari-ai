from pydantic import BaseModel
from typing import Optional

class ArticleEntity(BaseModel):
    id: str
    title: str
    content: str
    category: str
    similarity_score: Optional[float] = None
