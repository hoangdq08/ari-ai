from fastapi import APIRouter, UploadFile, File
from .schemas import DiagnoseResponse

router = APIRouter()

@router.post("/analyze", response_model=DiagnoseResponse)
async def analyze_disease(image: UploadFile = File(...)):
    """
    Phân tích hình ảnh bệnh cây bằng AI Vision.
    Tạm thời trả về Mock Data.
    """
    # TODO: Tích hợp Gemini Vision Pro
    return DiagnoseResponse(
        disease_name="[MOCK] Bệnh đạo ôn trên lúa",
        confidence=0.92,
        treatment="Sử dụng thuốc bảo vệ thực vật có chứa hoạt chất Tricyclazole.",
        preventive_measures="Vệ sinh đồng ruộng, dọn sạch tàn dư lúa bệnh."
    )
