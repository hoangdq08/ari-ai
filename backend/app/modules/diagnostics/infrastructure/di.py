from fastapi import Depends
from .mock_repository import MockDiagnosticsRepository
from ..domain.interfaces import IDiagnosticsRepository
from ..application.service import DiagnosticsService

def get_diagnostics_repository() -> IDiagnosticsRepository:
    """
    Cung cấp instance của Repository.
    Khi tích hợp model AI thật, ta sẽ đổi MockDiagnosticsRepository thành GeminiVisionRepository.
    """
    return MockDiagnosticsRepository()

def get_diagnostics_service(
    repository: IDiagnosticsRepository = Depends(get_diagnostics_repository)
) -> DiagnosticsService:
    """
    Cung cấp DiagnosticsService thông qua Dependency Injection.
    """
    return DiagnosticsService(repository=repository)
