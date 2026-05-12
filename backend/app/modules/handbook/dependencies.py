from fastapi import Depends
from .infrastructure.mock_repository import MockHandbookRepository
from .domain.repositories import HandbookRepository
from .application.service import HandbookService

def get_handbook_repository() -> HandbookRepository:
    """
    Trả về instance của Repository (có thể tráo đổi thành ChromaDB ở đây)
    """
    return MockHandbookRepository()

def get_handbook_service(
    repository: HandbookRepository = Depends(get_handbook_repository)
) -> HandbookService:
    """
    Khởi tạo và trả về Application Service với Dependency Injection
    """
    return HandbookService(repository=repository)
