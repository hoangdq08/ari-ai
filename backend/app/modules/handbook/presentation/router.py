from fastapi import APIRouter, Query
from .schemas import SearchHandbookResponse, SearchResultItem

router = APIRouter()

@router.get("/search", response_model=SearchHandbookResponse)
async def search_handbook(q: str = Query(..., min_length=2, description="Từ khóa tìm kiếm"), limit: int = Query(5, description="Số lượng kết quả trả về")):
    """
    Tra cứu kiến thức từ Cẩm nang Nông nghiệp (Vector DB).
    Tạm thời trả về Mock Data.
    """
    # TODO: Tích hợp ChromaDB Retrieval
    return SearchHandbookResponse(
        results=[
            SearchResultItem(
                title=f"[MOCK] Tài liệu liên quan đến: {q}",
                content="Đây là nội dung được trích xuất giả lập từ cơ sở dữ liệu Vector (ChromaDB)...",
                similarity_score=0.85
            )
        ]
    )
