from fastapi import Depends
from .infrastructure.mock_repository import MockChatRepository
from .domain.repositories import ChatRepository
from .application.service import ChatService

def get_chat_repository() -> ChatRepository:
    """
    Cung cấp instance của Chat Provider.
    Sau này sẽ đổi thành GeminiChatProvider hoặc RAGChatProvider.
    """
    return MockChatRepository()

def get_chat_service(repository: ChatRepository = Depends(get_chat_repository)) -> ChatService:
    """
    Khởi tạo và cung cấp ChatService thông qua DI.
    """
    return ChatService(repository=repository)
