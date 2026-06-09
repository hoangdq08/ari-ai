from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .source_policy import infer_reliability, source_penalty, source_review_decision, source_warnings


VIETNAMESE_RE = re.compile(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", re.IGNORECASE)
WORD_RE = re.compile(r"\w+", re.UNICODE)
LOW_VALUE_PATTERNS = [
    re.compile(r"\b(hotline|email|địa chỉ|website|zalo|facebook)\b", re.IGNORECASE),
    re.compile(r"\b(đặt hàng|mua ngay|giỏ hàng|sản phẩm liên quan)\b", re.IGNORECASE),
    re.compile(r"\b(copyright|all rights reserved)\b", re.IGNORECASE),
]
SEED_SOURCE_IDS = {
    "than_thu",
    "gi_sat_la_ca_phe",
    "dom_mat_cua",
    "cay_khoe",
    "coffee_leaf_rust",
    "cercospora_leaf_spot",
    "anthracnose",
    "healthy",
}


def build_data_quality_report(
    raw_dir: str | Path,
    cleaned_dir: str | Path,
    chunks_dir: str | Path,
    vector_store_path: str | Path,
) -> dict[str, Any]:
    raw_dir = Path(raw_dir)
    cleaned_dir = Path(cleaned_dir)
    chunks_dir = Path(chunks_dir)
    vector_store_path = Path(vector_store_path)

    source_reports = []
    for raw_path in sorted(raw_dir.glob("*.json")):
        raw_payload = _read_json(raw_path, default={})
        metadata = raw_payload.get("metadata") or {}
        source_id = metadata.get("source_id") or raw_path.stem
        if _is_seed_source(source_id, metadata):
            continue
        raw_text = raw_payload.get("raw_text") or ""
        cleaned_path = cleaned_dir / f"{source_id}.txt"
        cleaned_text = cleaned_path.read_text(encoding="utf-8") if cleaned_path.exists() else ""
        chunks = _read_json(chunks_dir / f"{source_id}.json", default=[])
        source_reports.append(_source_quality(source_id, metadata, raw_text, cleaned_text, chunks))

    vector_chunks = _read_json(vector_store_path, default=[])
    real_vector_chunks = [
        chunk
        for chunk in vector_chunks
        if isinstance(chunk, dict) and not _is_seed_source(chunk.get("metadata", {}).get("source_id", ""), chunk.get("metadata", {}))
    ] if isinstance(vector_chunks, list) else []
    warnings = Counter(warning for item in source_reports for warning in item["warnings"])
    reliability = Counter((item["reliability_level"] or "unknown") for item in source_reports)
    source_types = Counter((item["source_type"] or "unknown") for item in source_reports)
    review_status = Counter((item["review_status"] or "unknown") for item in source_reports)
    indexing_status = Counter((item["indexing_status"] or "unknown") for item in source_reports)

    # Split the chunk count by indexing status so dashboards can show the
    # truth: "indexable" should match `vector_chunk_count`; the rest are
    # held-for-review or blocked by the source review policy. Without this
    # split the FE used `abs(vector_chunks - chunks)` and reported a
    # misleading "lệch N chunk" warning even when the gap is exactly what
    # the quality gate is designed to produce.
    chunks_by_indexing_status: Counter[str] = Counter()
    for item in source_reports:
        status = item.get("indexing_status") or "unknown"
        chunks_by_indexing_status[status] += item.get("chunk_count", 0)

    total_chunks = sum(item["chunk_count"] for item in source_reports)
    chunks_indexable = chunks_by_indexing_status.get("indexed", 0)
    vector_count = len(real_vector_chunks)
    # The only number that should ever fire the "lệch" warning is the gap
    # between what the policy approved and what is actually persisted in
    # the vector store. Everything else is by design.
    real_index_drift = abs(chunks_indexable - vector_count)

    return {
        "summary": {
            "source_count": len(source_reports),
            "chunk_count": total_chunks,
            "vector_chunk_count": vector_count,
            "chunks_indexable": chunks_indexable,
            "chunks_held_for_review": chunks_by_indexing_status.get("held_for_review", 0),
            "chunks_blocked": chunks_by_indexing_status.get("blocked", 0),
            "chunks_by_indexing_status": dict(chunks_by_indexing_status),
            "real_index_drift": real_index_drift,
            "avg_quality_score": round(_avg([item["quality_score"] for item in source_reports]), 3),
            "warning_counts": dict(warnings),
            "reliability_counts": dict(reliability),
            "source_type_counts": dict(source_types),
            "review_status_counts": dict(review_status),
            "indexing_status_counts": dict(indexing_status),
        },
        "sources": sorted(source_reports, key=lambda item: (item["quality_score"], -item["cleaned_char_count"])),
    }


def _is_seed_source(source_id: str, metadata: dict[str, Any]) -> bool:
    file_name = metadata.get("file_name")
    seed_file_names = {f"{item}.json" for item in SEED_SOURCE_IDS}
    return bool(metadata.get("seed_sample") or source_id in SEED_SOURCE_IDS or file_name in seed_file_names)


def evaluate_retrieval_cases(cases: list[dict[str, Any]], rag: Any, top_k: int = 5) -> dict[str, Any]:
    results = []
    passed = 0
    # Aggregates for KPI reporting (slide 13).
    recall_at_k_total = 0.0
    reciprocal_rank_total = 0.0
    cite_rate_hits = 0
    refusal_hits = 0  # tracks cases where retrieval returned nothing => system should refuse
    for case in cases:
        question = case.get("question", "")
        expected_terms = [term.lower() for term in case.get("expected_terms", [])]
        expected_top_terms = [term.lower() for term in case.get("expected_top_terms", [])]
        chunks = rag.retrieve(question, top_k=top_k)
        top_joined = ""
        if chunks:
            top_chunk = chunks[0]
            top_joined = (
                top_chunk.get("text", "")
                + " "
                + str(top_chunk.get("metadata", {}).get("title") or "")
                + " "
                + str(top_chunk.get("metadata", {}).get("url") or "")
            ).lower()
        joined = " ".join(
            [
                chunk.get("text", "")
                + " "
                + str(chunk.get("metadata", {}).get("title") or "")
                + " "
                + str(chunk.get("metadata", {}).get("url") or "")
                for chunk in chunks
            ]
        ).lower()
        matched_terms = [term for term in expected_terms if term in joined]
        matched_top_terms = [term for term in expected_top_terms if term in top_joined]
        retrieval_pass = bool(chunks) and (not expected_terms or len(matched_terms) >= max(1, len(expected_terms) // 2))
        top_pass = not expected_top_terms or len(matched_top_terms) == len(expected_top_terms)
        is_pass = retrieval_pass and top_pass
        passed += int(is_pass)

        # KPI proxies (without gold chunk_ids we approximate against expected_terms).
        # Recall@k: portion of expected_terms that appear anywhere in retrieved chunks.
        recall_at_k = len(matched_terms) / len(expected_terms) if expected_terms else (1.0 if chunks else 0.0)
        recall_at_k_total += recall_at_k

        # MRR: rank of the first chunk that mentions ALL expected_top_terms.
        rr = 0.0
        if expected_top_terms and chunks:
            for index, chunk in enumerate(chunks, start=1):
                text_blob = (
                    chunk.get("text", "")
                    + " "
                    + str(chunk.get("metadata", {}).get("title") or "")
                    + " "
                    + str(chunk.get("metadata", {}).get("url") or "")
                ).lower()
                if all(term in text_blob for term in expected_top_terms):
                    rr = 1.0 / index
                    break
        elif chunks:
            rr = 1.0  # No constraint => the very first hit counts.
        reciprocal_rank_total += rr

        # Cite-rate: did we return at least one source for the answer?
        if chunks:
            cite_rate_hits += 1
        else:
            # No retrieval => system would (correctly) refuse the answer.
            refusal_hits += 1

        results.append(
            {
                "id": case.get("id"),
                "question": question,
                "passed": is_pass,
                "matched_terms": matched_terms,
                "matched_top_terms": matched_top_terms,
                "expected_terms": expected_terms,
                "expected_top_terms": expected_top_terms,
                "recall_at_k": round(recall_at_k, 3),
                "reciprocal_rank": round(rr, 3),
                "top_score": chunks[0].get("score", 0) if chunks else 0,
                "top_sources": [
                    {
                        "title": chunk.get("metadata", {}).get("title"),
                        "url": chunk.get("metadata", {}).get("url"),
                        "reliability_level": chunk.get("metadata", {}).get("reliability_level"),
                        "score": chunk.get("score"),
                    }
                    for chunk in chunks
                ],
            }
        )
    case_count = len(cases) or 1
    return {
        "summary": {
            "case_count": len(cases),
            "passed": passed,
            "failed": len(cases) - passed,
            "pass_rate": round(passed / case_count, 3),
            # KPI proxies (see docs/planning/slide-vs-code-alignment.md §5).
            "recall_at_k": round(recall_at_k_total / case_count, 3),
            "mrr": round(reciprocal_rank_total / case_count, 3),
            "cite_rate": round(cite_rate_hits / case_count, 3),
            "refusal_rate": round(refusal_hits / case_count, 3),
            "top_k": top_k,
        },
        "results": results,
    }


def _source_quality(source_id: str, metadata: dict[str, Any], raw_text: str, cleaned_text: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    warnings = []
    reliability_level = infer_reliability(metadata.get("url"), metadata.get("reliability_level"))
    if len(cleaned_text) < 500:
        warnings.append("cleaned_text_too_short")
    if len(raw_text) > 0 and len(cleaned_text) / len(raw_text) < 0.15:
        warnings.append("too_much_text_removed")
    if _noise_line_ratio(cleaned_text) > 0.18:
        warnings.append("possible_boilerplate_or_marketing_noise")
    if _duplicate_line_ratio(cleaned_text) > 0.16:
        warnings.append("high_duplicate_lines")
    if chunks and _avg([len(chunk.get("text", "")) for chunk in chunks]) < 350:
        warnings.append("chunks_too_small")
    if not metadata.get("url") and not metadata.get("file_name"):
        warnings.append("missing_source_locator")
    if reliability_level == "internet":
        warnings.append("internet_source_needs_review")
    warnings.extend(source_warnings(metadata.get("title"), metadata.get("url"), cleaned_text))

    quality_score = 1.0
    reliability_penalty = {"official": 0.0, "semi_official": 0.08, "manual": 0.05, "internet": 0.22}.get(reliability_level, 0.22)
    quality_score -= reliability_penalty
    quality_score -= min(0.45, len(warnings) * 0.07)
    quality_score -= min(0.2, _noise_line_ratio(cleaned_text))
    quality_score -= min(0.2, _duplicate_line_ratio(cleaned_text))
    quality_score -= source_penalty(metadata.get("title"), metadata.get("url"), cleaned_text)
    chunk_metadata = chunks[0].get("metadata", {}) if isinstance(chunks, list) and chunks else {}
    review = source_review_decision({**metadata, **chunk_metadata}, max(0.0, quality_score), warnings)
    return {
        "source_id": source_id,
        "title": metadata.get("title"),
        "url": metadata.get("url"),
        "file_name": metadata.get("file_name"),
        "source_type": metadata.get("source_type"),
        "reliability_level": reliability_level,
        "category": metadata.get("category") or chunk_metadata.get("category"),
        "category_label": metadata.get("category_label") or chunk_metadata.get("category_label"),
        "raw_char_count": len(raw_text),
        "cleaned_char_count": len(cleaned_text),
        "chunk_count": len(chunks) if isinstance(chunks, list) else 0,
        "avg_chunk_chars": round(_avg([len(chunk.get("text", "")) for chunk in chunks]), 1) if isinstance(chunks, list) else 0,
        "duplicate_line_ratio": round(_duplicate_line_ratio(cleaned_text), 3),
        "noise_line_ratio": round(_noise_line_ratio(cleaned_text), 3),
        "vietnamese_signal_ratio": round(_vietnamese_signal_ratio(cleaned_text), 3),
        "quality_score": round(max(0.0, quality_score), 3),
        "warnings": warnings,
        **review,
    }


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _avg(values: list[int | float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _duplicate_line_ratio(text: str) -> float:
    lines = [re.sub(r"\s+", " ", line.strip().lower()) for line in text.splitlines() if len(line.strip()) >= 24]
    if not lines:
        return 0.0
    counts = Counter(lines)
    duplicate_count = sum(count - 1 for count in counts.values() if count > 1)
    return duplicate_count / len(lines)


def _noise_line_ratio(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    noisy = sum(1 for line in lines if any(pattern.search(line) for pattern in LOW_VALUE_PATTERNS))
    return noisy / len(lines)


def _vietnamese_signal_ratio(text: str) -> float:
    words = WORD_RE.findall(text)
    if not words:
        return 0.0
    return sum(1 for word in words if VIETNAMESE_RE.search(word)) / len(words)
