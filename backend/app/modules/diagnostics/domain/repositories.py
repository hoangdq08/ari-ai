from abc import ABC, abstractmethod
from .models import DiagnosticResultEntity

class DiagnosticsRepository(ABC):
    @abstractmethod
    def analyze_image(self, file_bytes: bytes, filename: str) -> DiagnosticResultEntity:
        pass
