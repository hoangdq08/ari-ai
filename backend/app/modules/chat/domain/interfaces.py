from abc import ABC, abstractmethod
from typing import Optional
from .entities import ChatResponseEntity, TranscribeResponseEntity

class IChatProvider(ABC):
    @abstractmethod
    def send_message(self, message: str, session_id: Optional[str] = None) -> ChatResponseEntity:
        pass
        
    @abstractmethod
    def transcribe_audio(self, file_bytes: bytes, filename: str) -> TranscribeResponseEntity:
        pass
