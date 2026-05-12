from abc import ABC, abstractmethod
from typing import List
from .models import ArticleEntity

class HandbookRepository(ABC):
    @abstractmethod
    def search_articles(self, query: str, category: str = "Tất cả", limit: int = 5) -> List[ArticleEntity]:
        pass
