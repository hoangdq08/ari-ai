from typing import List
from ..domain.interfaces import IHandbookRepository
from ..domain.entities import ArticleEntity

class HandbookService:
    def __init__(self, repository: IHandbookRepository):
        self._repository = repository
        
    def search_articles(self, query: str, category: str = "Tất cả", limit: int = 5) -> List[ArticleEntity]:
        """
        Xử lý nghiệp vụ (Business Logic) cho việc tìm kiếm Cẩm nang.
        """
        # Tương lai có thể thêm logic phân tích ngữ nghĩa (NLP) ở đây trước khi gọi DB
        return self._repository.search_articles(query=query, category=category, limit=limit)
