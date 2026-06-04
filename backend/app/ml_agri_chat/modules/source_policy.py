from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


OFFICIAL_HOST_TOKENS = (
    "gov.vn",
    "mard.gov",
    "khuyennong",
    "vaas.vn",
    "wasiv",
    "vista.gov.vn",
    "ispae.vn",
)

SEMI_OFFICIAL_HOST_TOKENS = (
    ".edu",
    ".edu.vn",
    ".org",
    "tapchi",
    "researchgate",
    "vusta",
    "vov.vn",
    "vov1.vov.vn",
)

LOW_TRUST_HOST_TOKENS = (
    "qatarchemical",
    "qatar-chemical",
    "tuongnguyen",
    "sahari",
    "phanboncanada",
    "phanbonmiennam",
    "abachemical",
    "mekongagri",
    "kvf.vn",
    "vietcropchem",
    "hoachat",
    "shopee",
    "lazada",
    "tiki.vn",
)

COMMERCIAL_TEXT_PATTERNS = (
    re.compile(r"\b(công ty|tnhh|chemical|hóa chất|thuốc bvtv|mua ngay|đặt hàng|sản phẩm|hotline|zalo)\b", re.IGNORECASE),
    re.compile(r"\b(thuốc trừ|đại lý|bảng giá|giá bán|khuyến mãi|liên hệ mua|tư vấn sản phẩm)\b", re.IGNORECASE),
)

BAD_ENCODING_RE = re.compile(r"(Ã|Æ|áº|á»|Ä|Â)")
SOCIAL_HOST_TOKENS = ("facebook.com", "youtube.com", "youtu.be", "tiktok.com")
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "ml_pipeline" / "crawler" / "source_registry.json"


def load_source_registry() -> dict[str, Any]:
    try:
        with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def trusted_domains(level: str) -> tuple[str, ...]:
    registry = load_source_registry()
    domains = (registry.get("trusted_text_domains") or {}).get(level) or []
    return tuple(str(item).lower() for item in domains)


def infer_reliability(url: str | None, current: str | None = None) -> str:
    current_value = current or "internet"
    if current_value in {"official", "semi_official", "manual"}:
        return current_value
    host = urlparse(url or "").netloc.lower()
    if _host_matches(host, trusted_domains("official")):
        return "official"
    if _host_matches(host, trusted_domains("semi_official")):
        return "semi_official"
    if any(token in host for token in OFFICIAL_HOST_TOKENS):
        return "official"
    if any(token in host for token in SEMI_OFFICIAL_HOST_TOKENS):
        return "semi_official"
    return "internet"


def source_warnings(title: str | None, url: str | None, cleaned_text: str = "") -> list[str]:
    warnings: list[str] = []
    host = urlparse(url or "").netloc.lower()
    haystack = f"{title or ''} {url or ''} {cleaned_text[:1200]}".lower()
    reliability = infer_reliability(url, None)
    low_trust_hit = _host_matches(host, trusted_domains("low_trust")) or any(token in host or token in haystack for token in LOW_TRUST_HOST_TOKENS)
    if low_trust_hit and reliability != "official":
        warnings.append("low_trust_commercial_domain")
    if reliability != "official" and any(pattern.search(haystack) for pattern in COMMERCIAL_TEXT_PATTERNS):
        warnings.append("commercial_or_vendor_content")
    if BAD_ENCODING_RE.search(f"{title or ''} {cleaned_text[:400]}"):
        warnings.append("possible_vietnamese_encoding_error")
    if any(token in host for token in SOCIAL_HOST_TOKENS) and len(cleaned_text) < 800:
        warnings.append("social_source_too_short_for_rag")
    return warnings


def source_penalty(title: str | None, url: str | None, cleaned_text: str = "") -> float:
    warnings = source_warnings(title, url, cleaned_text)
    penalty = 0.0
    if "low_trust_commercial_domain" in warnings:
        penalty += 0.45
    if "commercial_or_vendor_content" in warnings:
        penalty += 0.32
    if "possible_vietnamese_encoding_error" in warnings:
        penalty += 0.22
    if "social_source_too_short_for_rag" in warnings:
        penalty += 0.2
    return min(0.9, penalty)


def source_review_decision(metadata: dict[str, Any], quality_score: float, warnings: list[str]) -> dict[str, Any]:
    registry = load_source_registry()
    policy = registry.get("trusted_data_policy") or {}
    reliability = infer_reliability(metadata.get("url"), metadata.get("reliability_level"))
    auto_levels = set(policy.get("auto_approve_reliability") or ["official", "semi_official"])
    critical_warnings = set(policy.get("critical_warnings") or [])
    blocking = [warning for warning in warnings if warning in critical_warnings]
    min_quality = float(policy.get("min_quality_for_auto_index") or 0.65)
    allow_manual = bool(policy.get("allow_manual_to_index", True))
    if reliability == "manual" and allow_manual and quality_score >= min_quality and not blocking:
        return {
            "review_status": "approved",
            "indexing_status": "indexed",
            "decision_reason": "manual source passed quality gate",
            "blocking_warnings": blocking,
        }
    if reliability in auto_levels and quality_score >= min_quality and not blocking:
        return {
            "review_status": "approved",
            "indexing_status": "indexed",
            "decision_reason": "trusted source passed quality gate",
            "blocking_warnings": blocking,
        }
    if quality_score < 0.25 or len(blocking) >= 3:
        return {
            "review_status": "rejected",
            "indexing_status": "blocked",
            "decision_reason": "critical quality/reliability risk",
            "blocking_warnings": blocking,
        }
    return {
        "review_status": policy.get("default_untrusted_status") or "needs_review",
        "indexing_status": "held_for_review",
        "decision_reason": "source needs human review before indexing",
        "blocking_warnings": blocking,
    }


def _host_matches(host: str, domains: tuple[str, ...]) -> bool:
    clean_host = host.lower().replace("www.", "")
    return any(clean_host == domain or clean_host.endswith(f".{domain}") for domain in domains)
