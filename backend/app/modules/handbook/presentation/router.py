from fastapi import APIRouter, Query
from .schemas import SearchHandbookResponse, SearchResultItem

router = APIRouter()

MOCK_ARTICLES = [
    {
        "id": "1",
        "title": "Phòng trừ bệnh đạo ôn hại lúa vụ Đông Xuân",
        "content": "Hướng dẫn nhận biết sớm vết bệnh hình mắt én trên lá và cách sử dụng thuốc đặc trị an toàn.",
        "category": "Lúa Gạo",
    },
    {
        "id": "2",
        "title": "Kỹ thuật ủ phân hữu cơ vi sinh từ phụ phẩm",
        "content": "Tận dụng rơm rạ, vỏ sầu riêng để ủ phân bón giúp tiết kiệm chi phí và cải tạo đất.",
        "category": "Kỹ thuật",
    },
    {
        "id": "3",
        "title": "Dấu hiệu nhận biết rầy nâu và cách phòng tránh",
        "content": "Các chu kỳ sinh trưởng của rầy nâu và phương pháp '3 giảm 3 tăng' hiệu quả cho bà con.",
        "category": "Côn trùng",
    },
    {
        "id": "4",
        "title": "Lịch gieo sạ lúa vùng Đồng bằng sông Cửu Long",
        "content": "Cập nhật lịch thời vụ mới nhất từ Bộ NN&PTNT để né rầy và ngập mặn.",
        "category": "Thời vụ",
    }
]

@router.get("/search", response_model=SearchHandbookResponse)
async def search_handbook(
    q: str = Query("", description="Từ khóa tìm kiếm"), 
    category: str = Query("Tất cả", description="Danh mục"),
    limit: int = Query(5, description="Số lượng kết quả trả về")
):
    """
    Tra cứu kiến thức từ Cẩm nang Nông nghiệp (Vector DB).
    Tạm thời trả về Mock Data.
    """
    filtered = MOCK_ARTICLES
    
    if category != "Tất cả":
        filtered = [a for a in filtered if a["category"] == category]
        
    if q.strip():
        lower_q = q.lower()
        filtered = [
            a for a in filtered 
            if lower_q in a["title"].lower() or lower_q in a["content"].lower()
        ]
        
    results = []
    for item in filtered[:limit]:
        results.append(
            SearchResultItem(
                id=item["id"],
                title=item["title"],
                content=item["content"],
                category=item["category"],
                similarity_score=0.95 if q.strip() else None
            )
        )
        
    return SearchHandbookResponse(results=results)
