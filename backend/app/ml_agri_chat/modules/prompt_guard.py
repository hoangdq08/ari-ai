"""Prompt safety helpers used by the chat endpoint.

Scope responsibilities (post-refactor):

- `validate_question`: blocks prompt-injection attempts only. Intent and
  out-of-scope handling has been moved to
  `intent_classifier.CascadeIntentClassifier`, which uses both a
  deterministic layer and an LLM layer for broader coverage. Keeping a
  separate injection check here matters because it has to fail closed
  before any LLM (including the classifier) is invoked with hostile
  input.
- `basic_chat_response`: short canned answers for greeting / thanks /
  goodbye / capability prompts. The cascade classifier also handles
  these, but keeping them here lets non-router callers (tests, future
  CLIs) re-use the canned text without depending on the LLM client.
- `validate_advice_text`: post-hoc safety guard for LLM advice output
  (no hallucinated chemicals / dosages / overpromises).

`DISCLAIMER` is re-exported because both the router and the advisor
templates embed it in their responses.
"""

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
    """Block hostile inputs before the cascade classifier runs.

    Returns `(True, None)` for safe inputs. Returns `(False, reason)` only
    when a prompt-injection pattern is detected. Out-of-scope filtering is
    delegated to the intent classifier so that we have a single source of
    truth for what counts as "off topic" and can leverage an LLM-backed
    fallback for ambiguous cases.
    """
    lowered = question.lower()
    if any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS):
        return False, "Không thể xử lý yêu cầu có dấu hiệu prompt injection."
    return True, None


def basic_chat_response(question: str) -> dict[str, str] | None:
    """Canned answer for greetings/thanks/goodbye/capability prompts.

    Kept as a side-channel API for tests and non-router callers. The
    production chat endpoint uses `CascadeIntentClassifier.canned_response`
    instead, which delegates to the same intent labels.
    """
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
