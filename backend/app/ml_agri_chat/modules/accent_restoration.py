import json
import re
from app.ml_agri_chat.modules.llm_client import LocalLLMClient

_RESTORE_PROMPT = """Bạn là trợ lý chuyên về nông nghiệp cây cà phê.
Nhiệm vụ: Khôi phục dấu tiếng Việt cho câu hỏi không dấu của nông dân.
GIỮ NGUYÊN NGỮ NGHĨA và SỐ LƯỢNG TỪ. Chỉ trả về MỘT JSON object với schema sau, không kèm giải thích:
{{"text": "<câu đã được thêm dấu>"}}

Ví dụ 1:
Input: "cay ca phe bi vang la va rung nhieu"
Output: {{"text": "cây cà phê bị vàng lá và rụng nhiều"}}

Ví dụ 2:
Input: "cho hoi thuoc tri rep sap"
Output: {{"text": "cho hỏi thuốc trị rệp sáp"}}

Input: "{question}"
Output:"""

def restore_vietnamese_accents(text: str, llm_client: LocalLLMClient) -> str:
    """Gọi LLM để khôi phục dấu tiếng Việt cho câu hỏi hoàn toàn không có dấu."""
    if not llm_client.is_enabled():
        return text
    
    prompt = _RESTORE_PROMPT.format(question=text[:500])
    result = llm_client.generate(
        prompt,
        temperature=0.0,
        timeout_override=2.0,  # Thời gian chờ rất ngắn để không làm chậm luồng
        response_format={"type": "json_object"},
    )
    
    if result.used_fallback or not result.text:
        return text
        
    try:
        raw_text = result.text.strip()
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        parsed = json.loads(raw_text)
        restored = parsed.get("text", text)
        if isinstance(restored, str) and restored.strip():
            return restored
    except Exception:
        pass
        
    return text
