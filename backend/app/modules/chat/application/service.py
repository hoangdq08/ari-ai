from typing import Optional
from ..domain.repositories import ChatRepository
from ..domain.models import ChatResponseEntity, TranscribeResponseEntity

class ChatService:
    def __init__(self, repository: ChatRepository):
        self._repository = repository
        
    def send_message(self, message: str, session_id: Optional[str] = None) -> ChatResponseEntity:
        """
        Nghiệp vụ xử lý gửi tin nhắn. 
        Tại đây có thể lưu lịch sử chat vào DB trước khi gọi tới AI Provider.
        """
        return self._repository.send_message(message=message, session_id=session_id)
        
    def transcribe_audio(self, file_bytes: bytes, filename: str) -> TranscribeResponseEntity:
        """
        Nghiệp vụ chuyển đổi giọng nói thành văn bản.
        """
        return self._repository.transcribe_audio(file_bytes=file_bytes, filename=filename)
