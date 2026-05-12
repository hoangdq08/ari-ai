from typing import Optional
from ..domain.repositories import ChatRepository
from ..domain.models import ChatResponseEntity, TranscribeResponseEntity

class MockChatRepository(ChatRepository):
    def send_message(self, message: str, session_id: Optional[str] = None) -> ChatResponseEntity:
        return ChatResponseEntity(
            reply=f"[MOCK] Trợ lý Nông Trí AI nhận được câu hỏi: '{message}'. Gợi ý cách xử lý: Phun thuốc X.",
            sources=["[MOCK] Cẩm nang Khuyến Nông VN - Tập 1"]
        )
        
    def transcribe_audio(self, file_bytes: bytes, filename: str) -> TranscribeResponseEntity:
        return TranscribeResponseEntity(
            text=f"[MOCK] Đây là văn bản được nhận diện từ file âm thanh '{filename}' của bạn."
        )
