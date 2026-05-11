from fastapi import APIRouter, UploadFile, File
from .schemas import ChatMessageRequest, ChatMessageResponse, TranscribeResponse

router = APIRouter()

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Chuyển đổi file âm thanh (giọng nói) thành văn bản (Speech-to-Text).
    Tạm thời trả về Mock Data.
    """
    # TODO: Tích hợp Faster-Whisper
    return TranscribeResponse(text="[MOCK] Đây là văn bản được nhận diện từ file âm thanh của bạn.")

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest):
    """
    Gửi tin nhắn text lên trợ lý AI và nhận phản hồi.
    Tạm thời trả về Mock Data.
    """
    # TODO: Tích hợp RAG / Gemini LLM
    return ChatMessageResponse(
        reply=f"[MOCK] Trợ lý Nông Trí AI nhận được câu hỏi: '{request.message}'. Gợi ý cách xử lý: Phun thuốc X.",
        sources=["[MOCK] Cẩm nang Khuyến Nông VN - Tập 1"]
    )
