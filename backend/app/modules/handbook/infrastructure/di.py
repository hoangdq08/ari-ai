from fastapi import Depends
from .mock_repository import MockHandbookRepository
from ..domain.interfaces import IHandbookRepository
from ..application.service import HandbookService

def get_handbook_repository() -> IHandbookRepository:
    """
    Trả về instance của Repository (có thể tráo đổi thành ChromaDB ở đây)
    """
    return MockHandbookRepository()

def get_handbook_service(
    repository: IHandbookRepository = Depends(get_handbook_repository)
) -> HandbookService:
    """
    Khởi tạo và trả về Application Service với Dependency Injection
    """
    return HandbookService(repository=repository)
