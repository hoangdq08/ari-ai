from abc import ABC, abstractmethod
from .entities import DiagnosticResultEntity

class IDiagnosticsRepository(ABC):
    @abstractmethod
    def analyze_image(self, file_bytes: bytes, filename: str) -> DiagnosticResultEntity:
        pass
