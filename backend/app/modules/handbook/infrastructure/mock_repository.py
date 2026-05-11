from typing import List
from ..domain.interfaces import IHandbookRepository
from ..domain.entities import ArticleEntity

MOCK_ARTICLES = [
    ArticleEntity(id="1", title="Phòng trừ bệnh đạo ôn hại lúa vụ Đông Xuân", content="Hướng dẫn nhận biết sớm vết bệnh hình mắt én trên lá và cách sử dụng thuốc đặc trị an toàn.", category="Lúa Gạo"),
    ArticleEntity(id="2", title="Kỹ thuật ủ phân hữu cơ vi sinh từ phụ phẩm", content="Tận dụng rơm rạ, vỏ sầu riêng để ủ phân bón giúp tiết kiệm chi phí và cải tạo đất.", category="Kỹ thuật"),
    ArticleEntity(id="3", title="Dấu hiệu nhận biết rầy nâu và cách phòng tránh", content="Các chu kỳ sinh trưởng của rầy nâu và phương pháp '3 giảm 3 tăng' hiệu quả cho bà con.", category="Côn trùng"),
    ArticleEntity(id="4", title="Lịch gieo sạ lúa vùng Đồng bằng sông Cửu Long", content="Cập nhật lịch thời vụ mới nhất từ Bộ NN&PTNT để né rầy và ngập mặn.", category="Thời vụ"),
]

class MockHandbookRepository(IHandbookRepository):
    def search_articles(self, query: str, category: str = "Tất cả", limit: int = 5) -> List[ArticleEntity]:
        filtered = MOCK_ARTICLES
        
        if category and category != "Tất cả":
            filtered = [a for a in filtered if a.category == category]
            
        if query and query.strip():
            lower_q = query.strip().lower()
            filtered = [
                a for a in filtered 
                if lower_q in a.title.lower() or lower_q in a.content.lower()
            ]
            # Set mock similarity score if queried
            for a in filtered:
                a.similarity_score = 0.95
                
        return filtered[:limit]
