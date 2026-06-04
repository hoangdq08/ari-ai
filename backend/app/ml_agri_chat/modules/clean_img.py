from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Sequence

try:
    import cv2
    import numpy as np
    from PIL import Image, UnidentifiedImageError
except ImportError:  # pragma: no cover - exercised when optional image deps are absent locally.
    cv2 = None
    np = None
    Image = None

    class UnidentifiedImageError(Exception):
        pass


ALLOWED_TYPES: Sequence[str] = ("image/jpeg", "image/png", "image/webp")


@dataclass
class ImageQualityResult:
    passed: bool
    issues: list[str]
    metrics: dict[str, float | int | str]


def validate_image_quality(image_bytes: bytes, content_type: str | None) -> ImageQualityResult:
    issues: list[str] = []
    metrics: dict[str, float | int | str] = {"content_type": content_type or "unknown"}

    if Image is None or np is None or cv2 is None:
        return ImageQualityResult(
            True,
            ["Bỏ qua kiểm tra chất lượng ảnh vì thiếu thư viện xử lý ảnh trong môi trường hiện tại."],
            metrics,
        )

    if content_type not in ALLOWED_TYPES:
        issues.append("Định dạng ảnh chưa hỗ trợ. Vui lòng dùng JPEG, PNG hoặc WebP.")

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError:
        return ImageQualityResult(False, ["Không đọc được file ảnh."], metrics)

    width, height = image.size
    metrics.update({"width": width, "height": height})
    if width < 320 or height < 320:
        issues.append("Ảnh quá nhỏ. Vui lòng tải ảnh tối thiểu 320x320.")

    arr = np.array(image)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    green_ratio = _green_ratio(arr)
    metrics.update(
        {
            "blur_score": round(blur_score, 2),
            "brightness": round(brightness, 2),
            "green_ratio": round(green_ratio, 3),
        }
    )

    if blur_score < 35:
        issues.append("Ảnh bị mờ, cần lấy nét rõ hơn.")
    if brightness < 45:
        issues.append("Ảnh quá tối.")
    if brightness > 220:
        issues.append("Ảnh quá sáng hoặc bị lóa.")
    if green_ratio < 0.03:
        issues.append("Ảnh chưa có đủ dấu hiệu lá/cây.")

    return ImageQualityResult(len(issues) == 0, issues, metrics)


def _green_ratio(rgb) -> float:
    red = rgb[:, :, 0].astype(np.int16)
    green = rgb[:, :, 1].astype(np.int16)
    blue = rgb[:, :, 2].astype(np.int16)
    mask = (green > red + 8) & (green > blue + 8) & (green > 45)
    return float(mask.mean())
