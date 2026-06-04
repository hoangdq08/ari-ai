from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaxonomyCategory:
    key: str
    label: str
    description: str
    terms: tuple[str, ...]
    queries: tuple[str, ...]


CATEGORIES: tuple[TaxonomyCategory, ...] = (
    TaxonomyCategory(
        key="dieu_kien_san_xuat",
        label="Điều kiện sản xuất",
        description="Đất, nước, khí hậu, giống, địa hình.",
        terms=("đất", "nước", "khí hậu", "địa hình", "vùng trồng", "độ cao", "thổ nhưỡng"),
        queries=(
            "điều kiện đất nước khí hậu địa hình trồng cà phê",
            "vùng trồng cà phê thổ nhưỡng độ cao khí hậu",
        ),
    ),
    TaxonomyCategory(
        key="thiet_lap_vuon",
        label="Thiết lập vườn trồng",
        description="Vườn ươm, làm đất, mật độ trồng, trồng mới, che bóng, hệ thống tưới.",
        terms=("vườn ươm", "làm đất", "mật độ", "trồng mới", "che bóng", "khoảng cách", "thiết lập vườn"),
        queries=(
            "thiết lập vườn trồng cà phê mật độ trồng cây che bóng",
            "kỹ thuật trồng mới cà phê làm đất vườn ươm",
        ),
    ),
    TaxonomyCategory(
        key="cham_soc_dinh_duong",
        label="Chăm sóc & dinh dưỡng",
        description="Tưới, bón phân, tỉa cành, tạo tán, quản lý cỏ, cải tạo đất.",
        terms=(
            "bón phân",
            "phân bón",
            "bổ sung dinh dưỡng",
            "dinh dưỡng",
            "tưới",
            "tỉa cành",
            "tạo tán",
            "quản lý cỏ",
            "cải tạo đất",
            "thiếu đạm",
            "thiếu lân",
            "thiếu kali",
        ),
        queries=(
            "chăm sóc cây cà phê tưới bón phân tỉa cành tạo tán",
            "quản lý dinh dưỡng thiếu đạm thiếu lân thiếu kali trên cà phê",
        ),
    ),
    TaxonomyCategory(
        key="bao_ve_cay_trong",
        label="Bảo vệ cây trồng",
        description="Bệnh, sâu hại, nấm, tuyến trùng, stress hạn/nhiệt, phòng ngừa và xử lý.",
        terms=("bệnh", "sâu", "nấm", "tuyến trùng", "rệp", "mọt", "vàng lá", "héo", "rụng lá", "phòng ngừa", "xử lý"),
        queries=(
            "bệnh hại cây cà phê triệu chứng nguyên nhân phòng trừ",
            "sâu bệnh hại cà phê tuyến trùng rệp mọt vàng lá phòng ngừa",
        ),
    ),
    TaxonomyCategory(
        key="giong_tai_canh",
        label="Giống & tái canh",
        description="Chọn giống, giống mới, ghép cải tạo, cây con, tái canh vườn già.",
        terms=("giống", "chọn giống", "cây giống", "tr4", "trs1", "ghép", "tái canh", "vườn già", "cải tạo"),
        queries=(
            "cách lựa chọn giống cà phê tr4 trs1 tái canh ghép cải tạo",
            "kỹ thuật chọn cây giống cà phê phù hợp vùng trồng",
        ),
    ),
    TaxonomyCategory(
        key="thu_hoach_sau_thu_hoach",
        label="Thu hoạch & sau thu hoạch",
        description="Thu hoạch, tỷ lệ trái chín, sơ chế, phơi/sấy, bảo quản, phân loại lỗi hạt.",
        terms=("thu hoạch", "trái chín", "sơ chế", "phơi", "sấy", "bảo quản", "phân loại", "lỗi hạt"),
        queries=(
            "thu hoạch cà phê tỷ lệ trái chín sơ chế phơi sấy bảo quản",
            "kiểm soát chất lượng hạt cà phê sau thu hoạch",
        ),
    ),
    TaxonomyCategory(
        key="quan_tri_kinh_te_tieu_chuan",
        label="Quản trị, kinh tế & tiêu chuẩn",
        description="Chi phí, năng suất, SOP, dữ liệu, tiêu chuẩn, bao tiêu, xuất khẩu.",
        terms=("chi phí", "kinh tế", "năng suất", "sop", "dữ liệu", "tiêu chuẩn", "vietgap", "4c", "bao tiêu", "xuất khẩu"),
        queries=(
            "quản trị sản xuất cà phê chi phí năng suất tiêu chuẩn bao tiêu",
            "tiêu chuẩn cà phê bền vững vietgap 4c xuất khẩu",
        ),
    ),
    TaxonomyCategory(
        key="khac_lien_quan",
        label="Khác liên quan",
        description="Các vấn đề cà phê/nông nghiệp có liên quan nhưng chưa thuộc nhóm chuẩn.",
        terms=("khác", "vấn đề khác", "tổng quan", "kinh nghiệm", "khuyến nghị", "rủi ro", "tư vấn", "câu hỏi chung"),
        queries=(
            "các vấn đề khác liên quan đến sản xuất cà phê",
            "kinh nghiệm tổng quan quản lý vườn cà phê và rủi ro thường gặp",
        ),
    ),
    TaxonomyCategory(
        key="giao_tiep_nguoi_dung",
        label="Giao tiếp",
        description="Lời chào, cảm ơn, hướng dẫn sử dụng, chuyển hướng câu hỏi ngoài phạm vi với EQ cao.",
        terms=("chào", "cảm ơn", "tạm biệt", "bạn là ai", "hướng dẫn", "hỗ trợ", "không liên quan", "ngoài phạm vi"),
        queries=(
            "mẫu giao tiếp trợ lý nông nghiệp với người dùng",
            "hướng dẫn người dùng đặt câu hỏi về cây cà phê một cách rõ ràng",
        ),
    ),
)

CATEGORY_MAP = {category.key: category for category in CATEGORIES}


def taxonomy_payload() -> list[dict[str, Any]]:
    return [
        {
            "key": category.key,
            "label": category.label,
            "description": category.description,
            "terms": list(category.terms),
            "queries": list(category.queries),
        }
        for category in CATEGORIES
    ]


def classify_text(text: str) -> dict[str, Any]:
    normalized = _normalize(text)
    scores: list[tuple[float, TaxonomyCategory, list[str]]] = []
    for category in CATEGORIES:
        matched = [term for term in category.terms if _normalize(term) in normalized]
        phrase_bonus = sum(1.5 for term in matched if " " in term)
        score = len(matched) + phrase_bonus
        scores.append((score, category, matched))

    best_score, category, matched_terms = max(scores, key=lambda item: item[0])
    confidence = min(1.0, best_score / 4.0) if best_score > 0 else 0.0
    if best_score <= 0:
        category = CATEGORY_MAP["khac_lien_quan"]
    return {
        "category": category.key,
        "category_label": category.label,
        "confidence": round(confidence, 3),
        "matched_terms": matched_terms,
    }


def classify_query(question: str) -> dict[str, Any]:
    normalized = _normalize(question)
    if any(term in normalized for term in ["benh gi", "bi gi", "trieu chung", "dau hieu", "vang la", "he o", "rụng lá", "sau benh"]):
        return {
            "category": "bao_ve_cay_trong",
            "category_label": CATEGORY_MAP["bao_ve_cay_trong"].label,
            "confidence": 0.9,
            "matched_terms": ["intent:bảo vệ cây trồng"],
        }
    return classify_text(question)


def is_vague_disease_question(question: str) -> bool:
    normalized = _normalize(question)
    asks_identity = any(term in normalized for term in ["benh gi", "bi gi", "la benh nao", "dang bi benh"])
    symptom_terms = [
        "vang",
        "dom",
        "set",
        "tham",
        "kho",
        "heo",
        "la",
        "than",
        "qua",
        "re",
        "mun",
        "bot",
        "rụng",
        "sau",
        "rep",
        "nam",
    ]
    has_symptom = any(term in normalized for term in symptom_terms)
    return asks_identity and not has_symptom


def category_matches(chunk: dict[str, Any], category_key: str) -> bool:
    metadata = chunk.get("metadata", {})
    if metadata.get("category") == category_key:
        return True
    text = f"{metadata.get('title') or ''} {metadata.get('url') or ''} {chunk.get('text') or ''}"
    return classify_text(text)["category"] == category_key


def enrich_metadata_with_taxonomy(metadata: dict[str, Any], text: str) -> dict[str, Any]:
    payload = classify_text(f"{metadata.get('title') or ''} {metadata.get('url') or ''} {text[:4000]}")
    enriched = dict(metadata)
    enriched["category"] = payload["category"]
    enriched["category_label"] = payload["category_label"]
    enriched["category_confidence"] = payload["confidence"]
    enriched["category_terms"] = payload["matched_terms"]
    return enriched


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    normalized = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    folded = without_marks.replace("đ", "d")
    return re.sub(r"\s+", " ", folded)
