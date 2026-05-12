from fastapi import APIRouter, UploadFile, File, Depends
from .schemas import ChatMessageRequest, ChatMessageResponse, TranscribeResponse
from ..application.service import ChatService
from ..dependencies import get_chat_service

router = APIRouter()

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Chuyển đổi file âm thanh (giọng nói) thành văn bản (Speech-to-Text).
    """
    file_bytes = await file.read()
    filename = file.filename or "audio.webm"
    
    result = chat_service.transcribe_audio(file_bytes=file_bytes, filename=filename)
    return TranscribeResponse(text=result.text)

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Gửi tin nhắn text lên trợ lý AI và nhận phản hồi.
    """
    result = chat_service.send_message(message=request.message, session_id=request.session_id)
    return ChatMessageResponse(reply=result.reply, sources=result.sources)
