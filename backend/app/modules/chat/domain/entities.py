from pydantic import BaseModel
from typing import List, Optional

class ChatResponseEntity(BaseModel):
    reply: str
    sources: List[str] = []

class TranscribeResponseEntity(BaseModel):
    text: str
