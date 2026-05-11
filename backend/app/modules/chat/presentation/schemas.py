from pydantic import BaseModel
from typing import List, Optional

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    reply: str
    sources: List[str] = []

class TranscribeResponse(BaseModel):
    text: str
