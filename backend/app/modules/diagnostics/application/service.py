from ..domain.repositories import DiagnosticsRepository
from ..domain.models import DiagnosticResultEntity

class DiagnosticsService:
    def __init__(self, repository: DiagnosticsRepository):
        self._repository = repository
        
    def analyze_image(self, file_bytes: bytes, filename: str) -> DiagnosticResultEntity:
        """
        Nghiệp vụ chẩn đoán bệnh từ hình ảnh.
        Có thể thêm bước kiểm tra dung lượng ảnh, định dạng ảnh, gọi model phân loại trước, v.v.
        """
        return self._repository.analyze_image(file_bytes=file_bytes, filename=filename)
