from __future__ import annotations

import re
import unicodedata


DISCLAIMER = "Thông tin chỉ mang tính hỗ trợ, không thay thế chuyên gia nông nghiệp."

INJECTION_PATTERNS = [
    r"bỏ qua (hướng dẫn|quy tắc|system)",
    r"ignore (previous|system|developer)",
    r"tiết lộ prompt",
    r"system prompt",
]

OUT_OF_SCOPE_TERMS = [
    "bệnh người",
    "chứng khoán",
    "vũ khí",
    "hack",
    "mật khẩu",
]

AGRICULTURE_SCOPE_TERMS = [
    "cà phê",
    "ca phe",
    "cafe",
    "coffee",
    "nông nghiệp",
    "nong nghiep",
    "cây trồng",
    "cay trong",
    "cây",
    "cay",
    "canh tác",
    "canh tac",
    "vườn",
    "vuon",
    "trang trại",
    "trang trai",
    "năng suất",
    "nang suat",
    "giống",
    "giong",
    "đất",
    "dat",
    "tưới",
    "tuoi",
    "phân bón",
    "phan bon",
    "sâu bệnh",
    "sau benh",
    "bệnh cây",
    "benh cay",
    "thu hoạch",
    "thu hoach",
    # Phương ngữ / từ địa phương Tây Nguyên, Tây Bắc, Nam Bộ.
    # Bổ sung để chống bias loại trừ người nói phương ngữ (trục Bias & Fairness).
    "rẫy",
    "ray",
    "đám rẫy",
    "dam ray",
    "trỉa",
    "tria",
    "sạ",
    "sa",
    "ruộng",
    "ruong",
    "đồng",
    "dong",
    "vụ mùa",
    "vu mua",
    "mùa vụ",
    "mua vu",
    "lúa",
    "lua",
    "hồ tiêu",
    "ho tieu",
    "tiêu",
    "tieu",
    "điều",
    "dieu",
    "sầu riêng",
    "sau rieng",
    "bơ",
    "bo",
    "ca cao",
    "cacao",
    "chè",
    "che",
    "mít",
    "mit",
    "rau",
    "trồng",
    "trong",
    "bón",
    "bon",
    "phun",
    "phòng trừ",
    "phong tru",
]

NON_AGRI_INVESTMENT_TERMS = [
    "chứng khoán",
    "chung khoan",
    "crypto",
    "coin",
    "forex",
    "bất động sản",
    "bat dong san",
    "cổ phiếu",
    "co phieu",
]

CHEMICAL_PATTERNS = [
    r"\b(carbendazim|mancozeb|glyphosate|chlorpyrifos|copper oxychloride)\b",
    r"(liều|pha|phun)\s+\d+.*(thuốc|hoạt chất|trừ|diệt|nấm|sâu|cỏ)",
]
PESTICIDE_CONTEXT = re.compile(r"(thuốc|hoạt chất|trừ sâu|trừ nấm|diệt cỏ|bảo vệ thực vật|bv tv)")
QUANTITY_PATTERN = re.compile(r"\b\d+([,.]\d+)?\s?(ml|g|kg|l|lit|lít|gram)\b")

GREETING_PATTERNS = {
    "hi",
    "hello",
    "helo",
    "hey",
    "chao",
    "xin chao",
    "chao ban",
    "chao ai",
}

THANKS_PATTERNS = {
    "cam on",
    "thanks",
    "thank you",
    "ok cam on",
    "oke cam on",
}

GOODBYE_PATTERNS = {
    "tam biet",
    "bye",
    "goodbye",
}

CAPABILITY_PATTERNS = [
    "ban lam duoc gi",
    "co the lam gi",
    "huong dan su dung",
    "hoi gi duoc",
    "ban la ai",
    "nong tri ai la gi",
]


def validate_question(question: str) -> tuple[bool, str | None]:
    normalized = _normalize_text(question)
    lowered = question.lower()
    compact = re.sub(r"[^\w\s]", " ", normalized)
    compact = re.sub(r"\s+", " ", compact).strip()
    if any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS):
        return False, "Không thể xử lý yêu cầu có dấu hiệu prompt injection."
    if (
        compact in GREETING_PATTERNS
        or compact in THANKS_PATTERNS
        or compact in GOODBYE_PATTERNS
        or any(pattern in compact for pattern in CAPABILITY_PATTERNS)
    ):
        return True, None
    if any(term in normalized for term in OUT_OF_SCOPE_TERMS):
        return False, _soft_scope_message()
    if not any(term in normalized for term in AGRICULTURE_SCOPE_TERMS):
        return False, _soft_scope_message()
    if "dau tu" in normalized:
        is_agriculture_context = any(term in normalized for term in AGRICULTURE_SCOPE_TERMS)
        is_non_agriculture_investment = any(term in normalized for term in NON_AGRI_INVESTMENT_TERMS)
        if is_non_agriculture_investment and not is_agriculture_context:
            return False, _soft_scope_message()
    return True, None


def basic_chat_response(question: str) -> dict[str, str] | None:
    normalized = _normalize_text(question)
    compact = re.sub(r"[^\w\s]", " ", normalized)
    compact = re.sub(r"\s+", " ", compact).strip()
    if compact in GREETING_PATTERNS:
        return {
            "answer": (
                "Chào bạn, mình là Nông Trí AI. Bạn có thể hỏi ngắn gọn về vườn cà phê: cây có triệu chứng gì, "
                "cần chăm sóc ra sao, bón phân/tưới nước thế nào, hoặc nên kiểm tra vấn đề nào trước."
            ),
            "confidence_level": "cao",
        }
    if compact in THANKS_PATTERNS:
        return {
            "answer": "Rất vui được hỗ trợ. Khi có thêm câu hỏi về vườn cà phê, bạn cứ hỏi tiếp nhé.",
            "confidence_level": "cao",
        }
    if compact in GOODBYE_PATTERNS:
        return {
            "answer": "Tạm biệt bạn. Chúc vườn cà phê khỏe và mùa vụ thuận lợi.",
            "confidence_level": "cao",
        }
    if any(pattern in compact for pattern in CAPABILITY_PATTERNS):
        return {
            "answer": (
                "Mình là trợ lý nông nghiệp cho cây cà phê. Mình phân nhóm câu hỏi trước, rồi chỉ dùng tài liệu "
                "đúng nhóm để trả lời: điều kiện trồng, thiết lập vườn, chăm sóc/dinh dưỡng, sâu bệnh, giống/tái canh, "
                "thu hoạch, quản trị sản xuất hoặc nhóm khác liên quan. Với lời chào/câu hỏi ngoài phạm vi, mình dùng lớp "
                "giao tiếp để phản hồi mềm và hướng bạn quay lại đúng phạm vi. Nếu nhóm đó chưa có tài liệu phù hợp, "
                "mình sẽ nói chưa đủ dữ liệu."
            ),
            "confidence_level": "cao",
        }
    return None


def _soft_scope_message() -> str:
    return (
        "Mình hiểu ý bạn, nhưng hiện Nông Trí AI được thiết kế để hỗ trợ trong phạm vi nông nghiệp và cây cà phê. "
        "Nếu bạn muốn, hãy thử hỏi theo hướng vườn cà phê, ví dụ: triệu chứng trên lá/quả/rễ, cách chăm sóc, "
        "bón phân, tưới nước, giống, thu hoạch hoặc dữ liệu đã crawl trong hệ thống."
    )


def validate_advice_text(text: str) -> list[str]:
    lowered = text.lower()
    issues: list[str] = []
    for pattern in CHEMICAL_PATTERNS:
        if re.search(pattern, lowered):
            issues.append("Nội dung có dấu hiệu bịa thuốc, liều lượng hoặc hóa chất.")
    if QUANTITY_PATTERN.search(lowered) and PESTICIDE_CONTEXT.search(lowered):
        issues.append("Nội dung có dấu hiệu đưa liều lượng thuốc/hóa chất cần chuyên gia xác nhận.")
    forbidden_claims = ["chắc chắn khỏi", "đảm bảo khỏi", "không có rủi ro"]
    for claim in forbidden_claims:
        if claim in lowered:
            issues.append("Nội dung có khẳng định quá mức hoặc không an toàn.")
    return issues


def _normalize_text(text: str) -> str:
    lowered = text.lower().strip()
    normalized = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_marks.replace("đ", "d")
