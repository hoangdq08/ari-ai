from __future__ import annotations

import re
from typing import Any

from .llm_client import LocalLLMClient
from .prompt_guard import DISCLAIMER, validate_advice_text


NON_VIETNAMESE_SCRIPT_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")
TRAINING_NOISE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bđào tạo\b",
        r"\bbài giảng\b",
        r"\bgiảng viên\b",
        r"\bhọc viên\b",
        r"\bkế hoạch bài giảng\b",
        r"\bphương pháp giảng\b",
        r"\bthảo luận nhóm\b",
        r"\bmục tiêu học tập\b",
        r"\bFFS\b",
        r"\bTOT\b",
        r"\btập huấn\b",
    ]
]
LOW_VALUE_LINE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"^\s*h\d+\s*:",
        r"^\s*hình\s+\d+",
        r"^\s*bài\s+\d+",
        r"^\s*kế hoạch bài giảng",
        r"^\s*\(?phút\)?\s*$",
        r"^\s*stt\b",
        r"^\s*toggle\b",
        r"^\s*menu\b",
    ]
]

CHAT_STOPWORDS = {
    "cách",
    "bón",
    "phân",
    "cho",
    "cây",
    "như",
    "thế",
    "nào",
    "theo",
    "trong",
    "cà",
    "phê",
    "coffee",
    "thông",
    "tin",
    "dựa",
    "trên",
    "tài",
    "liệu",
    "truy",
    "xuất",
    "điều",
    "kiện",
}


class ControlledAdvisor:
    """Controlled RAG advisor. Uses a local LLM only after retrieval."""

    def __init__(self, llm_client: LocalLLMClient | None = None) -> None:
        self.llm_client = llm_client or LocalLLMClient()

    def answer_chat(
        self,
        question: str,
        chunks: list[dict[str, Any]],
        history: list[dict[str, str]] | None = None,
        effective_question: str | None = None,
    ) -> dict[str, Any]:
        retrieval_question = effective_question or question
        if not chunks or chunks[0].get("score", 0) < 0.08:
            return {
                "answer": "Hiện chưa có đủ tài liệu trong hệ thống để kết luận.",
                "sources": [],
                "confidence_level": "thap",
                "safety_disclaimer": DISCLAIMER,
            }
        relevant_chunks = _filter_relevant_chunks(retrieval_question, chunks)
        relevance = _context_relevance(retrieval_question, relevant_chunks)
        if not relevance["enough"]:
            return {
                "answer": (
                    "Hiện chưa có đủ tài liệu trong hệ thống để kết luận. "
                    "Các nguồn truy xuất hiện tại chưa khớp trực tiếp với ý chính của câu hỏi."
                ),
                "sources": [],
                "confidence_level": "thap",
                "llm": {
                    # Configured primary; no LLM call was made here.
                    "provider": self.llm_client.provider,
                    "model": self.llm_client.model,
                    "used_fallback": True,
                    "error": f"Retrieved context rejected by relevance gate. query_terms={relevance['query_terms']} matched_terms={relevance['matched_terms']}",
                },
                "safety_disclaimer": DISCLAIMER,
            }

        context = "\n\n".join(_format_context_chunk(payload, retrieval_question) for payload in relevant_chunks[:5])
        if _is_site_investment_question(retrieval_question):
            return {
                "answer": _site_investment_answer(context),
                "sources": _source_payload(relevant_chunks),
                "confidence_level": "trung_binh" if _location_mentions(context) else "thap",
                "llm": {
                    "provider": self.llm_client.provider,
                    "model": self.llm_client.model,
                    "used_fallback": True,
                    "error": "Strategic site-selection question handled by deterministic RAG policy.",
                },
                "safety_disclaimer": DISCLAIMER,
            }

        conversation_context = _format_history(history or [])
        llm_result = self.llm_client.generate(_chat_prompt(question, context, conversation_context, retrieval_question))
        answer = llm_result.text or _fallback_chat_answer(context, retrieval_question)
        answer = _clean_contradictory_insufficient_prefix(answer, chunks)
        if answer.lstrip().lower().startswith("hiện chưa có đủ tài liệu") and relevance["enough"]:
            answer = _fallback_chat_answer(context, retrieval_question)
            llm_result.used_fallback = True
            llm_result.error = "LLM returned insufficient answer despite relevant retrieved context."
        if _has_non_vietnamese_script(answer):
            answer = _fallback_chat_answer(context, retrieval_question)
            llm_result.used_fallback = True
            llm_result.error = "LLM output contained non-Vietnamese script and was replaced by deterministic RAG fallback."
        answer = _clean_latin_language_artifacts(answer)
        answer = _remove_off_crop_lines(answer, retrieval_question)
        answer = _remove_product_lines(answer)
        answer = _ensure_single_disclaimer(answer)
        guard_issues = validate_advice_text(answer)
        if guard_issues:
            answer = (
                "Tài liệu có nhắc đến nội dung cần kiểm chứng thêm. Hệ thống không đưa ra tên thuốc, "
                "liều lượng hoặc hướng dẫn hóa chất khi chưa có xác nhận chuyên gia địa phương."
            )
            answer = _ensure_single_disclaimer(answer)
            llm_result.used_fallback = True
            llm_result.error = "; ".join(guard_issues)

        return {
            "answer": answer,
            "sources": _source_payload(relevant_chunks),
            "confidence_level": _confidence(relevant_chunks),
            "llm": {
                "provider": llm_result.provider,
                "model": llm_result.model,
                "used_fallback": llm_result.used_fallback,
                "error": llm_result.error,
            },
            "safety_disclaimer": DISCLAIMER,
        }

    def image_advice(self, prediction: Any, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if prediction.confidence < 0.60:
            return {
                "status": "khong_du_tin_cay",
                "summary": "Ảnh chưa đủ độ tin cậy để kết luận bệnh.",
                "explanation": "Confidence của vision model dưới 0.60, nên hệ thống không chẩn đoán bệnh từ ảnh này.",
                "recommendations": [
                    "Tải ảnh rõ hơn, đủ sáng, lấy nét vào lá hoặc bộ phận có triệu chứng.",
                    "Hỏi chuyên gia nông nghiệp địa phương nếu cây suy yếu nhanh."
                ],
                "sources": _source_payload(chunks),
                "safety_disclaimer": DISCLAIMER,
            }

        label_text = prediction.disease_label.replace("_", " ")
        if prediction.confidence < 0.85:
            status = "nghi_ngo"
            summary = f"Nghi ngờ/có dấu hiệu liên quan đến {label_text}."
        else:
            status = "chan_doan"
            summary = f"Kết quả chính từ vision model: {label_text}."

        if chunks:
            explanation = (
                f"Vision model trả nhãn {prediction.disease_label} với confidence {prediction.confidence:.2f}. "
                f"Các triệu chứng quan sát: {', '.join(prediction.observed_symptoms)}. "
                f"Tư vấn dưới đây chỉ dựa trên nguồn RAG đã truy xuất, không phải LLM tự chẩn đoán ảnh."
            )
            recommendations = _recommend_from_chunks(chunks)
        else:
            explanation = "Không tìm thấy nguồn phù hợp trong kho tri thức để diễn giải kết quả ảnh."
            recommendations = ["Hiện chưa có đủ tài liệu trong hệ thống để kết luận."]

        return {
            "status": status,
            "summary": summary,
            "explanation": explanation,
            "recommendations": recommendations,
            "sources": _source_payload(chunks),
            "safety_disclaimer": DISCLAIMER,
        }

    def llm_status(self) -> dict[str, Any]:
        return self.llm_client.status()


def _summarize_context(context: str, question: str) -> str:
    normalized_question = _normalize_query(question)
    context = _sanitize_context_text(context)
    if _is_pre_harvest_question(normalized_question):
        checklist = _build_pre_harvest_checklist(context)
        if checklist:
            return "\n".join(f"- {item}" for item in checklist)

    sentences = [_clean_summary_sentence(part) for part in re.split(r"[.\n]", context)]
    sentences = [part for part in sentences if 35 <= len(part) <= 260]
    if not sentences:
        return ""
    important_tokens = {
        token
        for token in re.findall(r"\w+", question.lower())
        if len(token) >= 4 and token not in CHAT_STOPWORDS
    }
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: (
            sum(1 for token in important_tokens if token in item[1].lower()),
            -item[0],
        ),
        reverse=True,
    )
    selected_indexes = sorted(index for index, _sentence in ranked[:4])
    selected = [sentences[index] for index in selected_indexes]
    return "\n".join(f"- {sentence}." for sentence in selected)


def _clean_summary_sentence(sentence: str) -> str:
    sentence = re.sub(r"\s+", " ", sentence).strip(" :-–—")
    sentence = re.sub(r"\b(Toggle|Menu|NỘI DUNG CHÍNH|Xem thêm)\b", "", sentence, flags=re.IGNORECASE).strip()
    sentence = re.sub(r"\bH\d+\s*:\s*", "", sentence, flags=re.IGNORECASE)
    sentence = re.sub(r"\bHình\s+\d+\s*:\s*", "", sentence, flags=re.IGNORECASE)
    if len(sentence) > 220:
        sentence = sentence[:217].rsplit(" ", 1)[0] + "..."
    return sentence


def _remove_off_crop_lines(answer: str, question: str) -> str:
    normalized_question = _normalize_query(question)
    if "ca phe" not in normalized_question:
        return answer
    kept = []
    for line in answer.splitlines():
        normalized_line = _normalize_query(line)
        if "ho tieu" in normalized_line and "ca phe" not in normalized_line:
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _remove_product_lines(answer: str) -> str:
    cleaned = re.sub(r"\s+hoặc\s+NUCAFE\b", "", answer, flags=re.IGNORECASE)
    kept = []
    product_like = re.compile(r"\b(NUCAFE|SA\s+Kali|Kali\s+sun)\b", re.IGNORECASE)
    for line in cleaned.splitlines():
        if product_like.search(line):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _format_context_chunk(chunk: dict[str, Any], question: str) -> str:
    metadata = chunk.get("metadata", {})
    title = metadata.get("title") or "Nguồn chưa đặt tên"
    url = metadata.get("url") or metadata.get("file_name") or "local"
    text = _extract_relevant_text(chunk.get("text", ""), question, max_chars=1100)
    return f"Nguồn: {title}\nURL/File: {url}\nNội dung:\n{text}"


def _format_history(history: list[dict[str, str]]) -> str:
    if not history:
        return "Không có lịch sử hội thoại trước đó."
    lines = []
    for item in history[-6:]:
        role = "Người dùng" if item.get("role") == "user" else "Trợ lý"
        content = re.sub(r"\s+", " ", item.get("content", "")).strip()[:700]
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "Không có lịch sử hội thoại trước đó."


def _chat_prompt(question: str, context: str, conversation_context: str = "", effective_question: str | None = None) -> str:
    return f"""Bạn là trợ lý RAG nông nghiệp tiếng Việt cho cây cà phê.

QUY TẮC BẮT BUỘC:
- Chỉ trả lời dựa trên CONTEXT đã truy xuất. Không dùng kiến thức ngoài context.
- Dùng LỊCH SỬ HỘI THOẠI để hiểu câu hỏi nối tiếp, nhưng không được lấy thông tin kỹ thuật từ lịch sử nếu CONTEXT không hỗ trợ.
- Nếu context không đủ, nói: "Hiện chưa có đủ tài liệu trong hệ thống để kết luận."
- Nếu context có thông tin liên quan nhưng thiếu chi tiết như liều lượng/số liệu, vẫn tóm tắt phần có trong context và nói rõ phần chưa đủ, không mở đầu bằng câu thiếu toàn bộ tài liệu.
- Không bịa tên thuốc, hoạt chất, liều lượng, nồng độ, lịch phun hoặc hóa chất.
- Không nêu tên sản phẩm thương mại nếu context không phải tài liệu chính thống.
- Có thể tóm tắt lượng phân bón/lịch bón nếu chính context đã nêu rõ.
- Không cam kết chắc chắn khỏi bệnh hoặc chắc chắn tăng năng suất.
- Trả lời ngắn gọn, có cấu trúc, tiếng Việt tự nhiên. Không chép nguyên văn context dài.
- Ưu tiên 3-5 gạch đầu dòng ngắn, mỗi dòng chỉ nêu một ý được context hỗ trợ.
- Chỉ dùng tiếng Việt. Không dùng tiếng Trung, tiếng Nhật, tiếng Hàn hoặc ngoại ngữ khác.
- Không tự thêm disclaimer nhiều lần. Kết thúc đúng một lần bằng câu: "{DISCLAIMER}"

CÂU HỎI:
{question}

CÂU HỎI ĐÃ LÀM RÕ THEO NGỮ CẢNH:
{effective_question or question}

LỊCH SỬ HỘI THOẠI:
{conversation_context or "Không có lịch sử hội thoại trước đó."}

CONTEXT:
{context}

TRẢ LỜI:
"""


def _fallback_chat_answer(context: str, question: str) -> str:
    normalized_question = _normalize_query(question)
    if _is_pre_harvest_question(normalized_question):
        checklist = _build_pre_harvest_checklist(_sanitize_context_text(context))
        if checklist:
            return (
                "Trước khi thu hoạch cà phê, bà con nên lưu ý:\n"
                f"{chr(10).join(f'- {item}' for item in checklist)}\n"
                "Nên đối chiếu thêm với tình trạng thực tế của vườn trước khi quyết định thời điểm hái hoặc cách xử lý sau thu hoạch."
            )

    summary = _summarize_context(context, question)
    if not summary:
        return "Hiện chưa có đủ tài liệu trong hệ thống để kết luận."
    return (
        "Dựa trên tài liệu đã truy xuất, có thể tham khảo:\n"
        f"{summary}\n"
        "Hệ thống chưa tự suy ra loại phân, liều lượng hoặc lịch bón ngoài phần tài liệu đã nêu. "
        "Nên đối chiếu với tình trạng vườn và hỏi cán bộ khuyến nông nếu cần quyết định kỹ thuật cụ thể."
    )


def _is_site_investment_question(question: str) -> bool:
    normalized = _normalize_query(question)
    has_investment = any(term in normalized for term in ["dau tu", "phat trien he thong", "mo trang trai"])
    asks_location = any(
        term in normalized
        for term in ["o dau", "vung nao", "khu vuc nao", "dia phuong nao", "tinh nao", "noi nao"]
    )
    has_coffee_context = any(term in normalized for term in ["ca phe", "coffee", "nong nghiep", "vuon", "trang trai"])
    return has_investment and asks_location and has_coffee_context


def _site_investment_answer(context: str) -> str:
    locations = _location_mentions(context)
    if locations:
        location_text = ", ".join(locations)
        location_note = (
            f"Tài liệu truy xuất có nhắc tới {location_text}, nhưng đó chưa đủ để kết luận đây là nơi nên đầu tư."
        )
    else:
        location_note = "Các tài liệu truy xuất chưa có dữ liệu địa điểm đủ rõ để so sánh vùng đầu tư."
    return (
        "Hiện chưa đủ tài liệu trong hệ thống để kết luận nên đầu tư phát triển hệ thống cà phê ở đâu.\n\n"
        f"{location_note} Để trả lời chính xác, hệ thống cần thêm dữ liệu theo vùng về khí hậu, đất, nước tưới, "
        "giống cà phê, hạ tầng thu mua/chế biến, chi phí vận hành, rủi ro sâu bệnh và chính sách địa phương.\n\n"
        "Với dữ liệu hiện có, chỉ nên dùng RAG để tham khảo tiêu chí kỹ thuật/canh tác, chưa dùng để ra quyết định chọn địa điểm đầu tư."
    )


def _location_mentions(context: str) -> list[str]:
    known_locations = [
        "Tây Nguyên",
        "Đắk Lắk",
        "Đắk Nông",
        "Gia Lai",
        "Lâm Đồng",
        "Kon Tum",
        "Tây Bắc",
        "Sơn La",
        "Điện Biên",
        "Lai Châu",
    ]
    lowered = context.lower()
    return [location for location in known_locations if location.lower() in lowered]


def _normalize_query(text: str) -> str:
    import unicodedata

    lowered = text.lower().strip()
    normalized = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_marks.replace("đ", "d")


def _context_relevance(question: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    query_terms = _important_query_terms(question)
    if not query_terms:
        return {"enough": True, "query_terms": [], "matched_terms": []}
    combined = " ".join(
        [
            chunk.get("text", "")
            + " "
            + str(chunk.get("metadata", {}).get("title") or "")
            + " "
            + str(chunk.get("metadata", {}).get("url") or "")
            for chunk in chunks[:5]
        ]
    )
    normalized_context = _normalize_query(combined)
    context_tokens = set(re.findall(r"\w+", normalized_context))
    matched_terms = sorted(term for term in query_terms if _term_matches(term, normalized_context, context_tokens))

    seed_terms = {"giong", "lua", "chon", "tr4", "trs1", "cay con", "tai canh", "ghep"}
    asks_seed_or_variety = bool(query_terms & seed_terms)
    disease_terms = {"than", "thu", "gi", "sat", "dom", "mat", "cua", "sau", "benh", "nam", "tuyen", "trung"}
    asks_disease = bool(query_terms & disease_terms)

    if asks_seed_or_variety:
        seed_signal = any(term in normalized_context for term in seed_terms)
        return {
            "enough": seed_signal and len(matched_terms) >= 1,
            "query_terms": sorted(query_terms),
            "matched_terms": matched_terms,
        }

    minimum_matches = 1 if asks_disease else min(2, len(query_terms))
    return {
        "enough": len(matched_terms) >= minimum_matches,
        "query_terms": sorted(query_terms),
        "matched_terms": matched_terms,
    }


def _filter_relevant_chunks(question: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query_terms = _important_query_terms(question)
    if not query_terms:
        return chunks
    normalized_question = _normalize_query(question)
    selected = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        text = _normalize_query(f"{metadata.get('title') or ''} {metadata.get('url') or ''} {chunk.get('text') or ''}")
        if _is_low_value_chunk_for_question(normalized_question, text):
            continue
        if _requires_exact_topic(normalized_question) and not _required_topic_matches(normalized_question, text):
            continue
        text_tokens = set(re.findall(r"\w+", text))
        match_count = sum(1 for term in query_terms if _term_matches(term, text, text_tokens))
        if match_count:
            item = dict(chunk)
            item["matched_query_terms"] = sorted(term for term in query_terms if _term_matches(term, text, text_tokens))
            selected.append(item)
    return selected or chunks[:1]


def _term_matches(term: str, normalized_text: str, text_tokens: set[str]) -> bool:
    if len(term) <= 3:
        return term in text_tokens
    return term in normalized_text


def _requires_exact_topic(normalized_question: str) -> bool:
    return "truoc thu hoach" in normalized_question or "thu hoach" in normalized_question


def _required_topic_matches(normalized_question: str, normalized_text: str) -> bool:
    if "truoc thu hoach" in normalized_question:
        required_terms = ("truoc thu hoach", "ve sinh vuon", "ty le qua chin", "san phoi", "thu hai")
        return any(term in normalized_text for term in required_terms)
    if "thu hoach" in normalized_question:
        harvest_terms = ("thu hoach", "qua chin", "che bien", "bao quan", "san phoi")
        return any(term in normalized_text for term in harvest_terms)
    return True


def _important_query_terms(question: str) -> set[str]:
    normalized = _normalize_query(question)
    stopwords = {_normalize_query(item) for item in CHAT_STOPWORDS}
    extra_stopwords = {
        "mot",
        "cac",
        "nhung",
        "neu",
        "nen",
        "duoc",
        "khong",
        "hien",
        "he",
        "thong",
        "ket",
        "luan",
        "tham",
        "khao",
    }
    tokens = {
        token
        for token in re.findall(r"\w+", normalized)
        if len(token) >= 3 and token not in stopwords and token not in extra_stopwords
    }
    return tokens


def _clean_contradictory_insufficient_prefix(answer: str, chunks: list[dict[str, Any]]) -> str:
    if not chunks or chunks[0].get("score", 0) < 0.12:
        return answer
    if not re.match(r"^\s*hiện chưa(?: có)? đủ tài liệu", answer, flags=re.IGNORECASE):
        return answer
    if len(answer) < 250:
        return answer
    cleaned = re.sub(
        r"^\s*Hiện chưa(?: có)? đủ tài liệu[^\n.]*[.]\s*Tuy nhiên,\s*",
        "Dựa trên các tài liệu đã truy xuất, ",
        answer,
        count=1,
        flags=re.IGNORECASE,
    )
    if cleaned == answer:
        cleaned = re.sub(
            r"^\s*Hiện chưa(?: có)? đủ tài liệu[^\n]*\n+",
            "Dựa trên các tài liệu đã truy xuất, có thể tóm tắt như sau:\n\n",
            answer,
            count=1,
            flags=re.IGNORECASE,
        )
    return cleaned


def _has_non_vietnamese_script(text: str) -> bool:
    return bool(NON_VIETNAMESE_SCRIPT_RE.search(text))


def _clean_latin_language_artifacts(text: str) -> str:
    replacements = {
        r"\batau\b": "hoặc",
        r"\bdan\b": "và",
    }
    cleaned = text
    for pattern, replacement in replacements.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return cleaned


def _ensure_single_disclaimer(answer: str) -> str:
    pattern = re.compile(re.escape(DISCLAIMER), re.IGNORECASE)
    stripped = pattern.sub("", answer).strip()
    stripped = re.sub(r"\n{3,}", "\n\n", stripped).strip()
    if not stripped:
        return DISCLAIMER
    return f"{stripped}\n\n{DISCLAIMER}"


def _extract_relevant_text(text: str, question: str, max_chars: int = 900) -> str:
    cleaned_text = _sanitize_context_text(text)
    lowered_text = cleaned_text.lower()
    query_tokens = [token for token in re.findall(r"\w+", _normalize_query(question)) if len(token) >= 4]
    important_tokens = [token for token in query_tokens if token not in CHAT_STOPWORDS]
    segments = [segment.strip() for segment in re.split(r"\n{2,}", cleaned_text) if len(segment.strip()) >= 30]
    if not segments:
        return cleaned_text[:max_chars]

    ranked_segments = sorted(
        segments,
        key=lambda segment: (
            _segment_priority(segment, important_tokens, query_tokens),
            -len(segment),
        ),
        reverse=True,
    )
    selected: list[str] = []
    current_length = 0
    for segment in ranked_segments:
        compact = _clean_summary_sentence(segment)
        if not compact or any(pattern.search(compact) for pattern in LOW_VALUE_LINE_PATTERNS):
            continue
        if compact in selected:
            continue
        projected = current_length + len(compact) + (2 if selected else 0)
        if projected > max_chars and selected:
            continue
        selected.append(compact)
        current_length = projected
        if current_length >= max_chars * 0.7 or len(selected) >= 4:
            break
    return "\n".join(selected)[:max_chars] if selected else cleaned_text[:max_chars]


def _segment_priority(segment: str, important_tokens: list[str], query_tokens: list[str]) -> tuple[int, int, int]:
    normalized_segment = _normalize_query(segment)
    matched_important = sum(1 for token in important_tokens if token in normalized_segment)
    matched_query = sum(1 for token in query_tokens if token in normalized_segment)
    bonus = 0
    if "truoc thu hoach" in normalized_segment:
        bonus += 4
    if any(term in normalized_segment for term in ("ve sinh vuon", "ty le qua chin", "thoi tiet", "san phoi", "che bien")):
        bonus += 2
    if _looks_like_training_noise(normalized_segment):
        bonus -= 6
    return (matched_important, matched_query, bonus)


def _sanitize_context_text(text: str) -> str:
    text = re.sub(r"Nguồn:\s*[^\n]+", " ", text)
    text = re.sub(r"URL/File:\s*[^\n]+", " ", text)
    text = text.replace("Nội dung:", " ")
    text = _fix_ocr_spacing(text)
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" :-–—")
        if not line:
            lines.append("")
            continue
        if any(pattern.search(line) for pattern in LOW_VALUE_LINE_PATTERNS):
            continue
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _fix_ocr_spacing(text: str) -> str:
    fixed = text
    fixed = re.sub(r"(\w)\s+([ƣơăâêôơưđ])", r"\1\2", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"([ƣơăâêôơưđ])\s+(\w)", r"\1\2", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"(\b\w)\s+(\w\b)", r"\1\2", fixed)
    fixed = re.sub(r"\s{2,}", " ", fixed)
    return fixed


def _is_pre_harvest_question(normalized_question: str) -> bool:
    return "truoc thu hoach" in normalized_question or (
        "thu hoach" in normalized_question and any(term in normalized_question for term in ("luu y", "cham soc", "chuan bi"))
    )


def _build_pre_harvest_checklist(context: str) -> list[str]:
    normalized_context = _normalize_query(context)
    items: list[str] = []
    if any(term in normalized_context for term in ("ve sinh dong ruong", "ve sinh vuon cay", "kiem tra vuon cay")):
        items.append("Kiểm tra vườn cây và vệ sinh đồng ruộng trước khi vào đợt hái.")
    if any(term in normalized_context for term in ("ty le qua chin", "qua chin", "thu hai")):
        items.append("Quan sát tỷ lệ quả chín để lên kế hoạch thu hái đúng thời điểm.")
    if any(term in normalized_context for term in ("tinh hinh thoi tiet", "thoi tiet")):
        items.append("Theo dõi thời tiết để bố trí ngày hái và tránh ảnh hưởng đến chất lượng quả.")
    if any(term in normalized_context for term in ("san phoi", "che bien", "phoi qua")):
        items.append("Chuẩn bị sân phơi, khu vực chế biến và điều kiện làm khô quả ngay sau thu hoạch.")
    if any(term in normalized_context for term in ("canh la", "tap chat", "qua xanh")):
        items.append("Lượm sạch cành lá, quả xanh và tạp chất lẫn trong quả sau khi thu hái.")
    return items[:5]


def _looks_like_training_noise(normalized_text: str) -> bool:
    return any(pattern.search(normalized_text) for pattern in TRAINING_NOISE_PATTERNS)


def _is_low_value_chunk_for_question(normalized_question: str, normalized_text: str) -> bool:
    if not _looks_like_training_noise(normalized_text):
        return False
    if _is_pre_harvest_question(normalized_question):
        return "truoc thu hoach" not in normalized_text and "qua chin" not in normalized_text
    return True


def _recommend_from_chunks(chunks: list[dict[str, Any]]) -> list[str]:
    text = " ".join(chunk["text"] for chunk in chunks[:2])
    sentences = [part.strip() for part in text.replace("\n", " ").split(".") if 45 <= len(part.strip()) <= 220]
    safe = [sentence for sentence in sentences if not validate_advice_text(sentence)]
    return safe[:4] or ["Theo dõi triệu chứng, cải thiện vệ sinh vườn và hỏi chuyên gia khi bệnh lan nhanh."]


def _source_payload(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    sources = []
    for chunk in chunks:
        metadata = chunk["metadata"]
        key = metadata["source_id"]
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "title": metadata.get("title"),
                "source_type": metadata.get("source_type"),
                "page": metadata.get("page"),
                "url": metadata.get("url"),
                "file_name": metadata.get("file_name"),
                "reliability_level": metadata.get("reliability_level"),
            }
        )
    return sources


def _confidence(chunks: list[dict[str, Any]]) -> str:
    top = chunks[0].get("score", 0) if chunks else 0
    if top >= 0.22:
        return "cao"
    if top >= 0.12:
        return "trung_binh"
    return "thap"
