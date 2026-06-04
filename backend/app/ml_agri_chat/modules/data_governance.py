from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlparse


GOVERNANCE_TOPICS = (
    {
        "key": "production_conditions",
        "label": "Điều kiện sản xuất",
        "terms": ("đất", "nước", "khí hậu", "địa hình", "vùng trồng", "độ cao", "thổ nhưỡng"),
    },
    {
        "key": "garden_setup",
        "label": "Thiết lập vườn",
        "terms": ("vườn ươm", "làm đất", "mật độ", "trồng mới", "che bóng", "khoảng cách"),
    },
    {
        "key": "nutrition",
        "label": "Chăm sóc & dinh dưỡng",
        "terms": ("bón phân", "phân bón", "dinh dưỡng", "tưới", "tỉa cành", "tạo tán", "cải tạo đất"),
    },
    {
        "key": "plant_protection",
        "label": "Bảo vệ cây trồng",
        "terms": ("bệnh", "sâu", "nấm", "tuyến trùng", "rệp", "mọt", "vàng lá", "phòng ngừa"),
    },
    {
        "key": "varieties",
        "label": "Giống & tái canh",
        "terms": ("giống", "chọn giống", "cây giống", "ghép", "tái canh", "vườn già", "cải tạo"),
    },
    {
        "key": "post_harvest",
        "label": "Thu hoạch & sau thu hoạch",
        "terms": ("thu hoạch", "trái chín", "sơ chế", "phơi", "sấy", "bảo quản", "phân loại"),
    },
    {
        "key": "standards",
        "label": "Quản trị & tiêu chuẩn",
        "terms": ("chi phí", "kinh tế", "năng suất", "tiêu chuẩn", "vietgap", "4c", "bao tiêu", "xuất khẩu"),
    },
)

REGION_TERMS = {
    "Tây Nguyên": ("tây nguyên", "đắk lắk", "dak lak", "đắk nông", "dak nong", "gia lai", "lâm đồng", "lam dong", "kon tum"),
    "Tây Bắc": ("tây bắc", "son la", "sơn la", "điện biên", "dien bien", "lai châu", "lai chau"),
    "Đông Nam Bộ": ("đông nam bộ", "dong nam bo", "bình phước", "binh phuoc", "đồng nai", "dong nai"),
}

HIGH_RISK_WARNINGS = {
    "possible_vietnamese_encoding_error",
    "low_trust_commercial_domain",
    "commercial_or_vendor_content",
    "too_much_text_removed",
    "possible_boilerplate_or_marketing_noise",
    "high_duplicate_lines",
}


def build_trust_report(data_quality_report: dict[str, Any]) -> dict[str, Any]:
    sources = data_quality_report.get("sources") or []
    summary = data_quality_report.get("summary") or {}
    source_count = len(sources)
    warning_counts = summary.get("warning_counts") or {}
    reliability_counts = summary.get("reliability_counts") or {}
    review_status_counts = summary.get("review_status_counts") or {}
    indexing_status_counts = summary.get("indexing_status_counts") or {}
    internet_count = int(reliability_counts.get("internet") or 0)
    official_count = int(reliability_counts.get("official") or 0)
    semi_official_count = int(reliability_counts.get("semi_official") or 0)
    approved_count = int(review_status_counts.get("approved") or 0)
    needs_review_count = int(review_status_counts.get("needs_review") or 0)
    rejected_count = int(review_status_counts.get("rejected") or 0)
    indexed_count = int(indexing_status_counts.get("indexed") or 0)
    held_count = int(indexing_status_counts.get("held_for_review") or 0)
    blocked_count = int(indexing_status_counts.get("blocked") or 0)
    warning_total = sum(int(value or 0) for value in warning_counts.values())
    high_risk_total = sum(int(warning_counts.get(key) or 0) for key in HIGH_RISK_WARNINGS)
    coverage = _topic_coverage(sources)
    region_coverage = _region_coverage(sources)
    domains = _domain_concentration(sources)
    top_domain_share = domains[0]["share"] if domains else 0
    topic_coverage_rate = _safe_avg([1 if item["count"] > 0 else 0 for item in coverage])
    official_share = official_count / source_count if source_count else 0
    reviewed_share = (official_count + semi_official_count) / source_count if source_count else 0
    internet_share = internet_count / source_count if source_count else 0
    risk_items = _risk_register(
        source_count=source_count,
        official_share=official_share,
        reviewed_share=reviewed_share,
        internet_share=internet_share,
        high_risk_total=high_risk_total,
        warning_total=warning_total,
        topic_coverage_rate=topic_coverage_rate,
        top_domain_share=top_domain_share,
        region_coverage=region_coverage,
    )
    trust_score = _trust_score(
        reviewed_share=reviewed_share,
        warning_density=warning_total / max(source_count, 1),
        high_risk_density=high_risk_total / max(source_count, 1),
        topic_coverage_rate=topic_coverage_rate,
        top_domain_share=top_domain_share,
        region_coverage_rate=_safe_avg([1 if item["count"] > 0 else 0 for item in region_coverage]),
    )
    return {
        "summary": {
            "trust_score": trust_score,
            "status": _score_status(trust_score),
            "source_count": source_count,
            "reviewed_source_share": round(reviewed_share, 3),
            "official_source_share": round(official_share, 3),
            "internet_source_share": round(internet_share, 3),
            "warning_total": warning_total,
            "high_risk_warning_total": high_risk_total,
            "approved_source_count": approved_count,
            "needs_review_source_count": needs_review_count,
            "rejected_source_count": rejected_count,
            "indexed_source_count": indexed_count,
            "held_source_count": held_count,
            "blocked_source_count": blocked_count,
            "review_status_counts": review_status_counts,
            "indexing_status_counts": indexing_status_counts,
            "topic_coverage_rate": round(topic_coverage_rate, 3),
            "top_domain_share": round(top_domain_share, 3),
        },
        "coverage": coverage,
        "region_coverage": region_coverage,
        "domain_concentration": domains[:12],
        "risk_register": risk_items,
        "controls": _governance_controls(),
        "model_card": _model_card(),
    }


def _topic_coverage(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for topic in GOVERNANCE_TOPICS:
        matched = []
        for source in sources:
            text = _source_text(source)
            terms = [term for term in topic["terms"] if term in text]
            if terms:
                matched.append(
                    {
                        "source_id": source.get("source_id"),
                        "title": source.get("title") or source.get("file_name") or source.get("source_id"),
                        "reliability_level": source.get("reliability_level") or "unknown",
                        "quality_score": source.get("quality_score") or 0,
                        "matched_terms": terms[:5],
                    }
                )
        official = sum(1 for item in matched if item["reliability_level"] == "official")
        rows.append(
            {
                "key": topic["key"],
                "label": topic["label"],
                "count": len(matched),
                "official_count": official,
                "review_status": "covered" if matched else "gap",
                "top_sources": sorted(matched, key=lambda item: item["quality_score"], reverse=True)[:4],
            }
        )
    return rows


def _region_coverage(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for label, terms in REGION_TERMS.items():
        matched = [source for source in sources if any(term in _source_text(source) for term in terms)]
        rows.append(
            {
                "label": label,
                "count": len(matched),
                "official_count": sum(1 for source in matched if source.get("reliability_level") == "official"),
                "status": "covered" if matched else "gap",
            }
        )
    return rows


def _domain_concentration(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for source in sources:
        url = source.get("url") or ""
        domain = urlparse(url).netloc.lower().replace("www.", "")
        if domain:
            counts[domain] += 1
    total = sum(counts.values())
    return [{"domain": domain, "count": count, "share": round(count / total, 3) if total else 0} for domain, count in counts.most_common()]


def _risk_register(
    *,
    source_count: int,
    official_share: float,
    reviewed_share: float,
    internet_share: float,
    high_risk_total: int,
    warning_total: int,
    topic_coverage_rate: float,
    top_domain_share: float,
    region_coverage: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    region_gaps = [item["label"] for item in region_coverage if item["count"] == 0]
    return [
        _risk(
            "source_bias",
            "Thiên lệch nguồn internet/thương mại",
            internet_share > 0.75 or reviewed_share < 0.25,
            f"{round(internet_share * 100)}% nguồn internet, {round(reviewed_share * 100)}% nguồn đã được tin cậy.",
            "Ưu tiên bổ sung tài liệu khuyến nông, viện/trường, tiêu chuẩn và nguồn bán chính thống.",
        ),
        _risk(
            "coverage_gap",
            "Thiếu độ phủ chủ đề",
            topic_coverage_rate < 0.85,
            f"Độ phủ chủ đề đạt {round(topic_coverage_rate * 100)}%.",
            "Bổ sung nguồn cho các nhóm có trạng thái gap trước khi dùng RAG làm khuyến nghị chính.",
        ),
        _risk(
            "regional_bias",
            "Thiên lệch vùng canh tác",
            bool(region_gaps),
            f"Vùng thiếu dữ liệu: {', '.join(region_gaps) if region_gaps else 'không có'}.",
            "Gắn metadata vùng và thu thập thêm nguồn cho vùng thiếu để tránh áp dụng một khuyến nghị cho mọi nơi.",
        ),
        _risk(
            "data_quality",
            "Rủi ro chất lượng dữ liệu",
            high_risk_total > max(10, source_count * 0.2),
            f"{high_risk_total} cảnh báo rủi ro cao trên tổng {warning_total} cảnh báo.",
            "Review encoding, nguồn thương mại, boilerplate và tài liệu bị làm sạch quá mạnh.",
        ),
        _risk(
            "source_concentration",
            "Tập trung vào ít domain",
            top_domain_share > 0.2,
            f"Domain lớn nhất chiếm {round(top_domain_share * 100)}% nguồn có URL.",
            "Giới hạn tỷ trọng domain trong tập eval/train và ưu tiên nguồn độc lập.",
        ),
        _risk(
            "feedback_loop",
            "Vòng lặp phản hồi suy biến",
            False,
            "Feedback hiện chưa được đưa thẳng vào dữ liệu train.",
            "Giữ luồng raw_feedback -> reviewed_feedback -> training_candidate -> approved_training_data.",
        ),
        _risk(
            "data_leakage",
            "Rò rỉ dữ liệu khi đánh giá",
            False,
            "Chưa phát hiện split train/test trong runtime hiện tại.",
            "Khi train model ảnh/RAG eval, split theo nguồn/thời gian, không split ngẫu nhiên theo từng chunk/ảnh.",
        ),
    ]


def _risk(key: str, title: str, active: bool, evidence: str, mitigation: str) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "severity": "high" if active else "controlled",
        "status": "needs_action" if active else "controlled",
        "evidence": evidence,
        "mitigation": mitigation,
    }


def _governance_controls() -> list[dict[str, str]]:
    return [
        {
            "name": "Không trả lời chắc khi thiếu ngữ cảnh",
            "status": "active",
            "detail": "Chat route có confidence_level, prompt guard và câu hỏi bổ sung cho bệnh mơ hồ.",
        },
        {
            "name": "Nguồn và cảnh báo đi kèm câu trả lời",
            "status": "active",
            "detail": "RAG trả nguồn; dashboard kiểm soát reliability, warnings và coverage.",
        },
        {
            "name": "Feedback không tự động thành nhãn huấn luyện",
            "status": "policy",
            "detail": "Feedback cần review trước khi đưa vào training candidate.",
        },
        {
            "name": "Chống leakage trong đánh giá",
            "status": "policy",
            "detail": "Train/test phải split theo thời gian/nguồn/vườn, không split ngẫu nhiên theo chunk.",
        },
    ]


def _model_card() -> dict[str, Any]:
    return {
        "system_name": "Nông Trí AI / ML-Agri-Chat",
        "intended_use": "Tư vấn tham khảo về canh tác cà phê, dữ liệu RAG và vận hành nguồn tri thức.",
        "not_intended_use": "Không thay thế chuyên gia nông nghiệp tại hiện trường, xét nghiệm bệnh, hoặc quyết định tài chính/pháp lý.",
        "primary_risks": [
            "Nguồn internet/thương mại có thể làm lệch khuyến nghị.",
            "Thiếu vùng trồng, mùa vụ, tuổi cây làm giảm độ chính xác.",
            "Ảnh mờ hoặc bối cảnh khác phân phối huấn luyện có thể gây dự đoán sai.",
        ],
        "user_explanation_pattern": "Nêu nguồn, mức tin cậy, giả định vùng/mùa vụ và thông tin còn thiếu.",
    }


def _trust_score(
    *,
    reviewed_share: float,
    warning_density: float,
    high_risk_density: float,
    topic_coverage_rate: float,
    top_domain_share: float,
    region_coverage_rate: float,
) -> int:
    score = 100
    score -= min(35, int((1 - reviewed_share) * 35))
    score -= min(20, int(warning_density * 6))
    score -= min(20, int(high_risk_density * 18))
    score -= min(15, int((1 - topic_coverage_rate) * 15))
    score -= min(10, int(max(0, top_domain_share - 0.12) * 60))
    score -= min(10, int((1 - region_coverage_rate) * 10))
    return max(0, min(100, score))


def _score_status(score: int) -> str:
    if score >= 80:
        return "ready"
    if score >= 60:
        return "review"
    return "high_risk"


def _source_text(source: dict[str, Any]) -> str:
    return " ".join(
        str(source.get(key) or "").lower()
        for key in ("title", "url", "file_name", "category", "category_label")
    )


def _safe_avg(values: list[int | float]) -> float:
    return sum(values) / len(values) if values else 0.0
