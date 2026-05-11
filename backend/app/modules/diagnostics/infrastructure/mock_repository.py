from ..domain.interfaces import IDiagnosticsRepository
from ..domain.entities import DiagnosticResultEntity

class MockDiagnosticsRepository(IDiagnosticsRepository):
    def analyze_image(self, file_bytes: bytes, filename: str) -> DiagnosticResultEntity:
        # Mock logic trả về kết quả giả lập
        return DiagnosticResultEntity(
            disease_name=f"[MOCK] Bệnh đạo ôn (từ: {filename})",
            confidence=0.92,
            treatment="Sử dụng thuốc bảo vệ thực vật có chứa hoạt chất Tricyclazole.",
            preventive_measures="Vệ sinh đồng ruộng, dọn sạch tàn dư lúa bệnh."
        )
