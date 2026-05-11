from typing import Optional
from ..domain.interfaces import IChatProvider
from ..domain.entities import ChatResponseEntity, TranscribeResponseEntity

class ChatService:
    def __init__(self, provider: IChatProvider):
        self._provider = provider
        
    def send_message(self, message: str, session_id: Optional[str] = None) -> ChatResponseEntity:
        """
        Nghiệp vụ xử lý gửi tin nhắn. 
        Tại đây có thể lưu lịch sử chat vào DB trước khi gọi tới AI Provider.
        """
        return self._provider.send_message(message=message, session_id=session_id)
        
    def transcribe_audio(self, file_bytes: bytes, filename: str) -> TranscribeResponseEntity:
        """
        Nghiệp vụ chuyển đổi giọng nói thành văn bản.
        """
        return self._provider.transcribe_audio(file_bytes=file_bytes, filename=filename)
