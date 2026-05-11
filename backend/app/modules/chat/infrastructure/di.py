from fastapi import Depends
from .mock_provider import MockChatProvider
from ..domain.interfaces import IChatProvider
from ..application.service import ChatService

def get_chat_provider() -> IChatProvider:
    """
    Cung cấp instance của Chat Provider.
    Sau này sẽ đổi thành GeminiChatProvider hoặc RAGChatProvider.
    """
    return MockChatProvider()

def get_chat_service(provider: IChatProvider = Depends(get_chat_provider)) -> ChatService:
    """
    Khởi tạo và cung cấp ChatService thông qua DI.
    """
    return ChatService(provider=provider)
