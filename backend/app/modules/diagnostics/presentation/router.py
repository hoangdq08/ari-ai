from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.shared.upload import max_image_bytes, read_upload_capped

from .schemas import DiagnoseResponse
from ..application.service import DiagnosticsService
from ..dependencies import get_diagnostics_service

router = APIRouter()


@router.post("/analyze", response_model=DiagnoseResponse)
async def analyze_disease(
    image: UploadFile = File(...),
    diagnostics_service: DiagnosticsService = Depends(get_diagnostics_service),
):
    """
    Phân tích hình ảnh bệnh cây bằng AI Vision.
    """
    file_bytes = await read_upload_capped(image, max_image_bytes(), "Image")
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Image file is empty.")
    filename = image.filename or "unknown.jpg"

    # Uỷ thác nghiệp vụ cho tầng Application
    result = diagnostics_service.analyze_image(file_bytes=file_bytes, filename=filename)

    # Map từ Entity (Domain) sang Schema (Presentation)
    return DiagnoseResponse(
        disease_name=result.disease_name,
        confidence=result.confidence,
        treatment=result.treatment,
        preventive_measures=result.preventive_measures,
    )
