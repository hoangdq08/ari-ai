from fastapi import APIRouter, Query, Depends
from .schemas import SearchHandbookResponse, SearchResultItem
from ..application.service import HandbookService
from ..dependencies import get_handbook_service

router = APIRouter()

@router.get("/search", response_model=SearchHandbookResponse)
async def search_handbook(
    q: str = Query("", description="Từ khóa tìm kiếm"), 
    category: str = Query("Tất cả", description="Danh mục"),
    limit: int = Query(5, description="Số lượng kết quả trả về"),
    handbook_service: HandbookService = Depends(get_handbook_service)
):
    """
    Tra cứu kiến thức từ Cẩm nang Nông nghiệp (Vector DB).
    """
    # Uỷ thác logic tìm kiếm cho tầng Application (Service)
    articles = handbook_service.search_articles(query=q, category=category, limit=limit)
    
    # Chuyển đổi từ Entity (Domain) sang Schema (Presentation)
    results = [
        SearchResultItem(
            id=item.id,
            title=item.title,
            content=item.content,
            category=item.category,
            similarity_score=item.similarity_score
        )
        for item in articles
    ]
        
    return SearchHandbookResponse(results=results)
