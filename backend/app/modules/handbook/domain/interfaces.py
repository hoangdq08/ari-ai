from abc import ABC, abstractmethod
from typing import List
from .entities import ArticleEntity

class IHandbookRepository(ABC):
    @abstractmethod
    def search_articles(self, query: str, category: str = "Tất cả", limit: int = 5) -> List[ArticleEntity]:
        pass
