from typing import List
from ..domain.repositories import HandbookRepository
from ..domain.models import ArticleEntity

class HandbookService:
    def __init__(self, repository: HandbookRepository):
        self._repository = repository
        
    def search_articles(self, query: str, category: str = "Tất cả", limit: int = 5) -> List[ArticleEntity]:
        """
        Xử lý nghiệp vụ (Business Logic) cho việc tìm kiếm Cẩm nang.
        """
        # Tương lai có thể thêm logic phân tích ngữ nghĩa (NLP) ở đây trước khi gọi DB
        return self._repository.search_articles(query=query, category=category, limit=limit)
