from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.ml_agri_chat.modules.clean_img import validate_image_quality
from app.ml_agri_chat.modules.data_governance import build_trust_report
from app.ml_agri_chat.modules.data_quality import build_data_quality_report, evaluate_retrieval_cases
from app.ml_agri_chat.modules.data_ingestion import DataIngestor, IngestedDocument
from app.ml_agri_chat.modules.document_chunking import chunk_document
from app.ml_agri_chat.modules.internet_crawler import InternetCrawler
from app.ml_agri_chat.modules.intent_classifier import (
    CascadeIntentClassifier,
    is_followup_question,
)
from app.ml_agri_chat.modules.llm_advisor import ControlledAdvisor
from app.ml_agri_chat.modules.logger import get_request_logger
from app.ml_agri_chat.modules.prompt_guard import DISCLAIMER, validate_question
from app.ml_agri_chat.modules.rag import AgriculturalRAG
from app.ml_agri_chat.modules.search_discovery import SearchDiscovery
from app.ml_agri_chat.modules.source_policy import source_review_decision, source_warnings
from app.ml_agri_chat.modules.taxonomy import CATEGORY_MAP, classify_query, enrich_metadata_with_taxonomy, is_vague_disease_question, taxonomy_payload
from app.ml_agri_chat.modules.text_cleaning import clean_text
from app.ml_agri_chat.modules.vision_model import CoffeeVisionClassifier, VisionPrediction
from app.shared.latency import latency_report as _latency_report
from app.shared.latency import stage_report as _stage_report
from app.shared.latency import StageTimer
from app.shared.rate_limit import (
    DEFAULT_ADMIN_LIMIT,
    DEFAULT_CHAT_LIMIT,
    DEFAULT_IMAGE_LIMIT,
    limiter,
)
from app.shared.upload import max_document_bytes, max_image_bytes, read_upload_capped

# Shared state, paths, singletons, and Pydantic models live in `_routes/_shared.py`
# so the per-domain route modules can register against the same `router`
# object without pulling 1300 lines of this file. The names imported below
# are re-exported here so existing call sites (e.g. tests doing
# `app.ml_agri_chat.router.rag`) keep working.
from app.ml_agri_chat._routes._shared import (
    ACTIVITY_EVENTS,
    BASE_DIR,
    CHUNKS_DIR,
    CLEANED_DIR,
    CRAWL_CANDIDATE_DIR,
    CRAWL_EVENTS,
    CRAWLER_DIR,
    ChatHistoryMessage,
    ChatRequest,
    CrawlUrlsRequest,
    DATA_DIR,
    EVALUATION_DIR,
    FeedbackRequest,
    IMAGE_DATASET_DIR,
    IngestUrlRequest,
    KB_DIR,
    MAX_ACTIVITY_EVENTS,
    MAX_CRAWL_EVENTS,
    MAX_DOCUMENT_BYTES,
    MAX_IMAGE_BYTES,
    ML_PIPELINE_DIR,
    RAW_DIR,
    REPORTS_DIR,
    RagEvaluateRequest,
    ResearchBatchRequest,
    ResearchSearchRequest,
    ResetDataRequest,
    VECTOR_DIR,
    advisor,
    crawler,
    ingestor,
    intent_classifier,
    log_activity as _log_activity,
    log_crawl_event as _log_crawl_event,
    rag,
    require_admin_token,
    router,
    search_discovery,
    short_hash as _short_hash,
    vision_classifier as classifier,
)
from app.ml_agri_chat._routes._helpers import (
    chunk_previews as _chunk_previews,
    chunks_for_trusted_rebuild as _chunks_for_trusted_rebuild,
    clean_chunk_store as _clean_chunk_store,
    clear_directory as _clear_directory,
    count_class_files as _count_class_files,
    count_files as _count_files,
    count_json_chunks as _count_json_chunks,
    count_rejected as _count_rejected,
    duplicate_result as _duplicate_result,
    ensure_taxonomy_labels as _ensure_taxonomy_labels,
    existing_chunk_count as _existing_chunk_count,
    indexing_quality_score as _indexing_quality_score,
    indexing_warnings as _indexing_warnings,
    ops_pipeline_status as _ops_pipeline_status,
    read_csv_file as _read_csv_file,
    read_json_file as _read_json_file,
    seed_knowledge_base_if_needed as _seed_knowledge_base_if_needed,
)


@router.on_event("startup")
def startup_seed() -> None:
    _ensure_taxonomy_labels()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "phase": "phase_1_rag_and_phase_2_image_mvp",
        "llm": advisor.llm_status(),
    }


def _chat_history(history: list[ChatHistoryMessage]) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in history[-8:]:
        role = "assistant" if item.role == "ai" else item.role
        content = " ".join(item.content.split())[:1200]
        if content:
            cleaned.append({"role": role, "content": content})
    return cleaned


def _effective_question(question: str, history: list[dict[str, str]]) -> str:
    """Rewrite the current question so RAG retrieval has the prior context.

    Short follow-ups like "ok chưa", "chiến chưa?", "vậy còn cây kia thì
    sao" carry no retrievable signal on their own - if we pass them to
    rag.retrieve() verbatim, the embedding/keyword search picks chunks
    based on the literal "chiến chưa" tokens and the LLM ends up
    answering in the wrong topic. The intent classifier already has the
    canonical follow-up detector; we reuse it here so the two pieces of
    code cannot drift apart.
    """
    current = " ".join(question.split())
    if not history or not is_followup_question(current):
        return current
    previous_user = next((item["content"] for item in reversed(history) if item["role"] == "user"), "")
    previous_assistant = next((item["content"] for item in reversed(history) if item["role"] == "assistant"), "")
    context = previous_user or previous_assistant
    if not context:
        return current
    # Always include the real prior turn so retrieval has the topic. When
    # the follow-up itself mentions a concrete technical noun (phân, bón,
    # tưới, ...) we tag the crop too; the previous version short-circuited
    # to a generic "cây cà phê" string and lost the actual context, which
    # is what produced the original off-topic answers.
    lowered = current.lower()
    concrete_terms = (
        "phân",
        "bón",
        "dinh dưỡng",
        "tưới",
        "nước",
        "giống",
        "tái canh",
        "thu hoạch",
        "sâu",
        "bệnh",
        "tuyến trùng",
        "rệp",
        "vàng lá",
        "tỉa",
        "tạo tán",
        "chi phí",
        "tiêu chuẩn",
    )
    enriched = f"{current}\nNgữ cảnh hội thoại trước đó: {context}"
    if any(term in lowered for term in concrete_terms):
        enriched += "\n(thuộc chủ đề cây cà phê)"
    return enriched


@router.post("/chat")
@limiter.limit(DEFAULT_CHAT_LIMIT)
def chat(request: Request, payload: ChatRequest) -> dict:
    request_id = str(uuid4())
    log = get_request_logger(request_id)
    conversation_history = _chat_history(payload.history)
    effective_question = _effective_question(payload.question, conversation_history)
    _log_activity(
        request_id,
        "chat",
        "received",
        "User chat request received",
        {
            # Privacy: do not log raw question content. Surface only length + hash so we can
            # correlate without persisting PII (place names, farmer names) into ACTIVITY_EVENTS.
            "question_length": len(payload.question),
            "question_hash": _short_hash(payload.question),
            "effective_question_hash": _short_hash(effective_question),
            "top_k": payload.top_k,
            "session_id": payload.session_id,
            "history_count": len(conversation_history),
        },
    )
    allowed, reason = validate_question(effective_question)
    if not allowed:
        log.info("chat_blocked reason=%s", reason)
        _log_activity(request_id, "chat", "blocked", "Prompt guard blocked chat", {"reason": reason})
        return {
            "answer": reason,
            "sources": [],
            "confidence_level": "thap",
            "safety_disclaimer": DISCLAIMER,
        }

    with StageTimer("intent") as t_intent:
        intent_result = intent_classifier.classify(
            payload.question, history=conversation_history
        )
    log.info(
        "chat_intent label=%s confidence=%.2f source=%s reason=%s elapsed_ms=%.1f",
        intent_result.label,
        intent_result.confidence,
        intent_result.source,
        intent_result.reason,
        t_intent.elapsed_ms,
    )
    canned = CascadeIntentClassifier.canned_response(intent_result.label)
    if canned is not None:
        _log_activity(
            request_id,
            "chat",
            "intent_short_circuit",
            "Answered from intent classifier without calling RAG/LLM",
            {
                "intent": intent_result.label,
                "confidence": round(intent_result.confidence, 2),
                "source": intent_result.source,
                "intent_ms": round(t_intent.elapsed_ms, 1),
            },
        )
        return {**canned, "intent": intent_result.label, "session_id": payload.session_id}

    # For follow-ups, classifying the bare current text (e.g. "chiến chưa")
    # picks the wrong taxonomy bucket because the topic words live in the
    # prior turn. Re-use the previous user message's category instead. The
    # effective_question already carries the prior turn for retrieval, so
    # the two signals stay in sync.
    if conversation_history and is_followup_question(payload.question):
        previous_user = next(
            (item["content"] for item in reversed(conversation_history) if item["role"] == "user"),
            "",
        )
        route = classify_query(previous_user) if previous_user else classify_query(effective_question)
    else:
        route = classify_query(effective_question)
    if is_vague_disease_question(effective_question):
        return {
            "answer": (
                "Câu hỏi thuộc nhóm Bảo vệ cây trồng, nhưng chưa đủ triệu chứng để suy luận bệnh. "
                "Bạn hãy mô tả thêm bộ phận bị hại, màu vết bệnh, mặt trên/mặt dưới lá, tình trạng quả/cành/rễ, "
                "hoặc upload ảnh rõ để hệ thống kiểm tra bằng luồng ảnh."
            ),
            "sources": [],
            "confidence_level": "thap",
            "routing": route,
            "safety_disclaimer": DISCLAIMER,
        }
    with StageTimer("retrieval") as t_retrieval:
        chunks = rag.retrieve(effective_question, top_k=payload.top_k, category_key=route["category"])
    with StageTimer("advisor") as t_advisor:
        answer = advisor.answer_chat(payload.question, chunks, history=conversation_history, effective_question=effective_question)
    log.info(
        "chat retrieved_source_ids=%s intent_ms=%.1f retrieval_ms=%.1f advisor_ms=%.1f",
        [c["metadata"]["source_id"] for c in chunks],
        t_intent.elapsed_ms,
        t_retrieval.elapsed_ms,
        t_advisor.elapsed_ms,
    )
    _log_activity(
        request_id,
        "chat",
        "rag_answered",
        "RAG chat response generated",
        {
            "retrieved_source_ids": [c["metadata"]["source_id"] for c in chunks],
            "source_count": len(answer.get("sources", [])),
            "confidence_level": answer.get("confidence_level"),
            "category": route,
            "intent_ms": round(t_intent.elapsed_ms, 1),
            "retrieval_ms": round(t_retrieval.elapsed_ms, 1),
            "advisor_ms": round(t_advisor.elapsed_ms, 1),
        },
    )
    return {**answer, "routing": route, "session_id": payload.session_id}


@router.post("/ingest-document", dependencies=[Depends(require_admin_token)])
async def ingest_document(
    file: UploadFile = File(...),
    source_type: str = Form("manual"),
    title: Optional[str] = Form(None),
    reliability_level: str = Form("manual"),
) -> dict:
    request_id = str(uuid4())
    log = get_request_logger(request_id)
    if reliability_level not in {"official", "semi_official", "internet", "manual"}:
        raise HTTPException(status_code=400, detail="Invalid reliability_level.")

    file_bytes = await read_upload_capped(file, MAX_DOCUMENT_BYTES, "Document")
    if not file_bytes:
        raise HTTPException(status_code=400, detail="File is empty.")

    ingested = ingestor.ingest_file(file_bytes, file.filename or "document.txt", source_type, title, reliability_level)
    if ingested.is_duplicate:
        result = _duplicate_result(ingested)
        log.info("ingest_document duplicate source_id=%s duplicate_of=%s", ingested.source_id, ingested.duplicate_of)
        _log_activity(
            request_id,
            "chunking",
            "duplicate_document_skipped",
            "Uploaded document already exists; skipped chunk/vector write",
            {"source_id": ingested.source_id, "file_name": file.filename, "duplicate_of": ingested.duplicate_of},
        )
        return {"request_id": request_id, **result}
    result = _clean_chunk_store(ingested.source_id, ingested.raw_text, ingested.metadata)
    log.info("ingest_document source_id=%s chunks=%s", ingested.source_id, result["chunks_added"])
    _log_activity(
        request_id,
        "chunking",
        "document_ingested",
        "Uploaded document extracted, cleaned and chunked",
        {"source_id": ingested.source_id, "file_name": file.filename, "chunks_created": result["chunks_created"]},
    )
    return {"request_id": request_id, **result}


@router.post("/ingest-url", dependencies=[Depends(require_admin_token)])
def ingest_url(payload: IngestUrlRequest) -> dict:
    request_id = str(uuid4())
    log = get_request_logger(request_id)
    try:
        ingested = ingestor.ingest_url(payload.url, payload.title, payload.reliability_level)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not ingest URL: {exc}") from exc
    if ingested.is_duplicate:
        result = _duplicate_result(ingested)
        log.info("ingest_url duplicate source_id=%s duplicate_of=%s", ingested.source_id, ingested.duplicate_of)
        _log_activity(
            request_id,
            "chunking",
            "duplicate_url_skipped",
            "URL content already exists; skipped chunk/vector write",
            {"source_id": ingested.source_id, "url": payload.url, "duplicate_of": ingested.duplicate_of},
        )
        return {"request_id": request_id, **result}
    result = _clean_chunk_store(ingested.source_id, ingested.raw_text, ingested.metadata)
    log.info("ingest_url source_id=%s chunks=%s", ingested.source_id, result["chunks_added"])
    _log_activity(
        request_id,
        "chunking",
        "url_ingested",
        "URL extracted, cleaned and chunked",
        {"source_id": ingested.source_id, "url": payload.url, "chunks_created": result["chunks_created"]},
    )
    return {"request_id": request_id, **result}


@router.post("/crawl-urls", dependencies=[Depends(require_admin_token)])
def crawl_urls(payload: CrawlUrlsRequest) -> dict:
    request_id = str(uuid4())
    log = get_request_logger(request_id)
    _log_activity(
        request_id,
        "crawl",
        "started",
        "Manual crawl started",
        {"url_count": len(payload.urls), "collect_links": payload.collect_links, "max_pages": payload.max_pages},
    )
    results = crawler.crawl_urls(
        payload.urls,
        reliability_level=payload.reliability_level,
        max_pages=payload.max_pages,
        collect_links=payload.collect_links,
        same_domain_only=payload.same_domain_only,
        progress_callback=lambda event: _log_crawl_event(request_id, event),
        force=payload.force,
    )

    ingested = []
    duplicates: list[dict] = []
    skipped: list[dict] = []
    for item in results:
        if item.status == "duplicate" and item.source_id:
            existing_metadata = (_read_json_file(RAW_DIR / f"{item.source_id}.json", default={}) or {}).get("metadata") or {}
            duplicates.append(
                {
                    "source_id": item.source_id,
                    "url": item.url,
                    "title": item.title or existing_metadata.get("title"),
                    "source_type": item.source_type or existing_metadata.get("source_type"),
                    "existed_since": existing_metadata.get("crawled_at"),
                    "chunks_count": _existing_chunk_count(item.source_id),
                }
            )
            _log_crawl_event(
                request_id,
                {
                    "event": "duplicate_skipped",
                    "url": item.url,
                    "source_id": item.source_id,
                    "chunks_created": _existing_chunk_count(item.source_id),
                    "chunks_added": 0,
                },
            )
            _log_activity(
                request_id,
                "chunking",
                "duplicate_skipped",
                "Crawled source already exists; skipped chunk/vector write",
                {"source_id": item.source_id, "url": item.url},
            )
            continue
        if item.status == "skipped":
            skipped.append(
                {
                    "url": item.url,
                    "reason": item.error,
                    "content_type": item.content_type,
                }
            )
            continue
        if item.status != "ingested" or not item.source_id:
            continue
        raw_path = RAW_DIR / f"{item.source_id}.json"
        if not raw_path.exists():
            continue
        raw_payload = _read_json_file(raw_path, default={})
        result = _clean_chunk_store(item.source_id, raw_payload.get("raw_text", ""), raw_payload.get("metadata", {}))
        _log_crawl_event(
            request_id,
            {
                "event": "chunked",
                "url": item.url,
                "source_id": item.source_id,
                "chunks_created": result["chunks_created"],
                "chunks_added": result["chunks_added"],
            },
        )
        _log_activity(
            request_id,
            "chunking",
            "chunked",
            "Crawled source cleaned and chunked",
            {"source_id": item.source_id, "url": item.url, "chunks_created": result["chunks_created"], "chunks_added": result["chunks_added"]},
        )
        cleaned_path = CLEANED_DIR / f"{item.source_id}.txt"
        cleaned_text = cleaned_path.read_text(encoding="utf-8") if cleaned_path.exists() else ""
        ingested.append(
            {
                "source_id": item.source_id,
                "title": raw_payload.get("metadata", {}).get("title"),
                "url": raw_payload.get("metadata", {}).get("url"),
                "source_type": raw_payload.get("metadata", {}).get("source_type"),
                "raw_text_char_count": len(raw_payload.get("raw_text", "")),
                "cleaned_text_char_count": len(cleaned_text),
                "raw_text_preview": raw_payload.get("raw_text", "")[:2000],
                "cleaned_text_preview": cleaned_text[:2000],
                "cleaned_text": cleaned_text,
                "chunk_previews": _chunk_previews(CHUNKS_DIR / f"{item.source_id}.json"),
                **result,
            }
        )

    log.info(
        "crawl_urls urls=%s ingested=%s duplicate=%s skipped=%s failed=%s force=%s",
        len(payload.urls),
        sum(1 for item in results if item.status == "ingested"),
        sum(1 for item in results if item.status == "duplicate"),
        sum(1 for item in results if item.status == "skipped"),
        sum(1 for item in results if item.status == "failed"),
        payload.force,
    )
    _log_activity(
        request_id,
        "crawl",
        "completed",
        "Manual crawl completed",
        {
            "url_count": len(payload.urls),
            "ingested": sum(1 for item in results if item.status == "ingested"),
            "duplicate": sum(1 for item in results if item.status == "duplicate"),
            "skipped": sum(1 for item in results if item.status == "skipped"),
            "failed": sum(1 for item in results if item.status == "failed"),
            "force": payload.force,
        },
    )
    return {
        "request_id": request_id,
        "results": [item.to_dict() for item in results],
        "ingested": ingested,
        "duplicates": duplicates,
        "skipped": skipped,
    }


@router.post("/research-search", dependencies=[Depends(require_admin_token)])
def research_search(payload: ResearchSearchRequest) -> dict:
    request_id = str(uuid4())
    log = get_request_logger(request_id)
    _log_activity(
        request_id,
        "research",
        "search_started",
        "Research search started",
        {"query": payload.query, "max_results": payload.max_results, "auto_crawl": payload.auto_crawl},
    )
    try:
        candidates = search_discovery.search(payload.query, max_results=payload.max_results)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Search failed: {exc}") from exc

    crawl_payload = None
    if payload.auto_crawl and candidates:
        selected = [item.url for item in candidates[: payload.crawl_top_k]]
        crawl_results = crawler.crawl_urls(
            selected,
            reliability_level="internet",
            max_pages=len(selected),
            collect_links=False,
            same_domain_only=True,
            progress_callback=lambda event: _log_crawl_event(request_id, event),
        )
        ingested = []
        for item in crawl_results:
            if item.status == "duplicate" and item.source_id:
                _log_crawl_event(
                    request_id,
                    {
                        "event": "duplicate_skipped",
                        "url": item.url,
                        "source_id": item.source_id,
                        "chunks_created": _existing_chunk_count(item.source_id),
                        "chunks_added": 0,
                    },
                )
                continue
            if item.status != "ingested" or not item.source_id:
                continue
            raw_path = RAW_DIR / f"{item.source_id}.json"
            if not raw_path.exists():
                continue
            raw_payload = _read_json_file(raw_path, default={})
            result = _clean_chunk_store(item.source_id, raw_payload.get("raw_text", ""), raw_payload.get("metadata", {}))
            _log_crawl_event(
                request_id,
                {
                    "event": "chunked",
                    "url": item.url,
                    "source_id": item.source_id,
                    "chunks_created": result["chunks_created"],
                    "chunks_added": result["chunks_added"],
                },
            )
            cleaned_path = CLEANED_DIR / f"{item.source_id}.txt"
            cleaned_text = cleaned_path.read_text(encoding="utf-8") if cleaned_path.exists() else ""
            ingested.append(
                {
                    "source_id": item.source_id,
                    "title": raw_payload.get("metadata", {}).get("title"),
                    "url": raw_payload.get("metadata", {}).get("url"),
                    "source_type": raw_payload.get("metadata", {}).get("source_type"),
                    "raw_text_char_count": len(raw_payload.get("raw_text", "")),
                    "cleaned_text_char_count": len(cleaned_text),
                    "raw_text_preview": raw_payload.get("raw_text", "")[:2000],
                    "cleaned_text_preview": cleaned_text[:2000],
                    "cleaned_text": cleaned_text,
                    "chunk_previews": _chunk_previews(CHUNKS_DIR / f"{item.source_id}.json"),
                    **result,
                }
            )
        crawl_payload = {"results": [item.to_dict() for item in crawl_results], "ingested": ingested}

    log.info("research_search query=%s candidates=%s auto_crawl=%s", payload.query, len(candidates), payload.auto_crawl)
    _log_activity(
        request_id,
        "research",
        "search_completed",
        "Research search completed",
        {"query": payload.query, "candidate_count": len(candidates), "auto_crawl": payload.auto_crawl},
    )
    return {
        "request_id": request_id,
        "query": payload.query,
        "candidates": [candidate.to_dict() for candidate in candidates],
        "crawl": crawl_payload,
    }


@router.post("/research-batch", dependencies=[Depends(require_admin_token)])
def research_batch(payload: ResearchBatchRequest) -> dict:
    request_id = str(uuid4())
    topics = [_normalize_topic(item) for item in payload.queries]
    topics = [item for index, item in enumerate(topics) if item and item not in topics[:index]]
    if not topics:
        raise HTTPException(status_code=400, detail="Danh sách truy vấn trống.")

    _log_activity(
        request_id,
        "research",
        "batch_started",
        "Batch research started",
        {"query_count": len(topics), "max_results": payload.max_results, "target_per_query": payload.target_per_query},
    )

    groups = []
    unique_candidates: dict[str, dict] = {}
    for topic in topics:
        route = classify_query(topic)
        candidates: dict[str, dict] = {}
        searched_queries = []
        for search_query in _research_query_variants(topic, route):
            searched_queries.append(search_query)
            try:
                found = search_discovery.search(search_query, max_results=payload.max_results)
            except Exception:
                found = []

            for candidate in found:
                item = candidate.to_dict()
                if _number(item.get("relevance_score")) <= 0 or not item.get("url"):
                    continue
                item.update(
                    {
                        "batch_topic": topic,
                        "batch_group": route["category_label"],
                        "batch_group_key": route["category"],
                        "searched_query": search_query,
                    }
                )
                previous = candidates.get(item["url"])
                if not previous or _number(item.get("relevance_score")) > _number(previous.get("relevance_score")):
                    candidates[item["url"]] = item

            if len(candidates) >= min(payload.target_per_query, payload.max_results):
                break

        sorted_candidates = sorted(candidates.values(), key=lambda item: _number(item.get("relevance_score")), reverse=True)[
            : payload.max_results
        ]
        groups.append(
            {
                "topic": topic,
                "group": {"key": route["category"], "label": route["category_label"]},
                "routing": route,
                "searched_queries": searched_queries,
                "candidates": sorted_candidates,
            }
        )
        for candidate in sorted_candidates:
            current = unique_candidates.get(candidate["url"])
            if not current or _number(candidate.get("relevance_score")) > _number(current.get("relevance_score")):
                unique_candidates[candidate["url"]] = candidate

    candidates = sorted(unique_candidates.values(), key=lambda item: _number(item.get("relevance_score")), reverse=True)
    selected_urls = [item["url"] for item in candidates]
    _log_activity(
        request_id,
        "research",
        "batch_completed",
        "Batch research completed",
        {
            "query_count": len(topics),
            "candidate_count": len(candidates),
            "selected_url_count": len(selected_urls),
        },
    )
    return {
        "request_id": request_id,
        "topics": topics,
        "groups": groups,
        "candidates": candidates,
        "selected_urls": selected_urls,
    }


def _normalize_topic(value: str) -> str:
    return " ".join(str(value or "").split())


def _research_query_variants(topic: str, route: dict) -> list[str]:
    category = CATEGORY_MAP.get(route.get("category", ""))
    normalized = topic.lower()
    has_coffee = "cà phê" in normalized or "ca phe" in normalized or "coffee" in normalized
    coffee_topic = topic if has_coffee else f"{topic} cà phê"
    variants = [
        coffee_topic,
        f"{coffee_topic} khuyến nông",
        f"{coffee_topic} tài liệu kỹ thuật",
        f"{coffee_topic} PDF",
    ]
    if category:
        variants.extend(category.queries)
        variants.append(f"{coffee_topic} {category.description}")

    seen = set()
    unique = []
    for item in variants:
        cleaned = _normalize_topic(item)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            unique.append(cleaned)
    return unique[:8]


def _number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@router.get("/sources")
def sources() -> dict[str, list[dict]]:
    return {"sources": rag.sources()}


@router.get("/taxonomy")
def taxonomy() -> dict[str, list[dict]]:
    return {"categories": taxonomy_payload()}


@router.get("/data-quality")
def data_quality() -> dict:
    return build_data_quality_report(RAW_DIR, CLEANED_DIR, CHUNKS_DIR, VECTOR_DIR / "chunks.json")


@router.get("/trust-report")
def trust_report() -> dict:
    quality = build_data_quality_report(RAW_DIR, CLEANED_DIR, CHUNKS_DIR, VECTOR_DIR / "chunks.json")
    return build_trust_report(quality)


@router.get("/crawl-events")
def crawl_events(limit: int = 120) -> dict:
    return {"events": CRAWL_EVENTS[-max(1, min(limit, 2000)) :]}


@router.get("/admin/ops-events", dependencies=[Depends(require_admin_token)])
def admin_ops_events(limit: int = 200) -> dict:
    bounded_limit = max(1, min(limit, 500))
    return {
        "events": ACTIVITY_EVENTS[-bounded_limit:],
        "pipelines": _ops_pipeline_status(),
        # Slide 13 KPI: latency p50 ≤ 3.0s. Real per-route stats here, and
        # per-stage breakdown of /chat (intent vs retrieval vs advisor) so
        # tuning is targeted instead of guessing.
        "latency": _latency_report(),
        "latency_stages": _stage_report(),
    }


@router.get("/admin/intent-metrics", dependencies=[Depends(require_admin_token)])
def admin_intent_metrics() -> dict:
    """Aggregated counters from the cascade intent classifier.

    Per-process counters since worker start; with multi-worker deployments
    scrape each worker (e.g. behind a load balancer with sticky session).
    Use this to tune `l1_confidence_threshold` and decide whether the
    deterministic layer covers enough traffic.
    """
    return {"intent_classifier": intent_classifier.stats()}


@router.post("/admin/rag-reembed-all", dependencies=[Depends(require_admin_token)])
def admin_rag_reembed_all() -> dict:
    """Force every chunk in the vector store to be re-embedded with the
    currently active embedding provider.

    Useful after switching `NONGTRI_EMBEDDING_PROVIDER` or when the index
    drifts from the source chunks. The auto-migration in
    `EmbeddingStore._load()` also re-embeds on version mismatch at startup,
    but this endpoint lets ops trigger the same work without a restart.
    """
    updated = rag.store.reembed_all()
    _log_activity(
        "system",
        "chunking",
        "rag_reembed_all",
        "All vector store chunks re-embedded with active provider",
        {
            "updated": updated,
            "embedding_version": rag.store.embedding_version,
        },
    )
    return {
        "updated": updated,
        "embedding_version": rag.store.embedding_version,
    }


@router.post("/admin/reset-rag-data", dependencies=[Depends(require_admin_token)])
@limiter.limit(DEFAULT_ADMIN_LIMIT)
def reset_rag_data(request: Request, payload: ResetDataRequest) -> dict:
    for directory in [RAW_DIR, CLEANED_DIR, CHUNKS_DIR, VECTOR_DIR, CRAWL_CANDIDATE_DIR]:
        _clear_directory(directory)
    rag.rebuild([])
    CRAWL_EVENTS.clear()
    ACTIVITY_EVENTS.clear()
    if payload.seed_knowledge_base:
        _seed_knowledge_base_if_needed()
    _log_crawl_event(
        "system",
        {
            "event": "reset_rag_data",
            "seed_knowledge_base": payload.seed_knowledge_base,
            "source_count": len(rag.sources()),
        },
    )
    _log_activity(
        "system",
        "admin",
        "reset_rag_data",
        "RAG data directories cleared",
        {"seed_knowledge_base": payload.seed_knowledge_base, "source_count": len(rag.sources())},
    )
    return {
        "status": "reset",
        "seed_knowledge_base": payload.seed_knowledge_base,
        "source_count": len(rag.sources()),
        "chunk_count": _count_json_chunks(CHUNKS_DIR),
    }


@router.post("/rag-evaluate")
def rag_evaluate(payload: RagEvaluateRequest) -> dict:
    cases_path = EVALUATION_DIR / "rag_eval_cases.json"
    cases = _read_json_file(cases_path, default=[])
    if not isinstance(cases, list) or not cases:
        raise HTTPException(status_code=400, detail="No RAG evaluation cases found.")
    return evaluate_retrieval_cases(cases, rag, top_k=payload.top_k)


@router.post("/rag-rebuild-index", dependencies=[Depends(require_admin_token)])
def rag_rebuild_index() -> dict:
    chunk_dicts: list[dict] = []
    held_files: list[str] = []
    blocked_files: list[str] = []
    for path in sorted(CHUNKS_DIR.glob("*.json")):
        chunks = _read_json_file(path, default=[])
        indexable, decision = _chunks_for_trusted_rebuild(path.stem, chunks)
        if indexable:
            chunk_dicts.extend(indexable)
        elif decision.get("indexing_status") == "blocked":
            blocked_files.append(path.stem)
        else:
            held_files.append(path.stem)
    added = rag.rebuild(chunk_dicts)
    _log_activity(
        "system",
        "chunking",
        "rag_index_rebuilt",
        "Trusted vector index rebuilt from approved chunk files",
        {
            "chunk_files": len(list(CHUNKS_DIR.glob("*.json"))),
            "chunks_indexed": added,
            "held_files": len(held_files),
            "blocked_files": len(blocked_files),
        },
    )
    return {
        "status": "rebuilt",
        "chunk_files": len(list(CHUNKS_DIR.glob("*.json"))),
        "chunks_indexed": added,
        "held_files": held_files,
        "blocked_files": blocked_files,
    }


@router.get("/crawl-dashboard")
def crawl_dashboard() -> dict:
    image_metadata = _read_json_file(IMAGE_DATASET_DIR / "raw" / "metadata.json", default=[])
    download_failures = _read_json_file(IMAGE_DATASET_DIR / "raw" / "download_failures.json", default=[])
    source_registry = _read_json_file(CRAWLER_DIR / "source_registry.json", default={})
    queries = _read_json_file(CRAWLER_DIR / "search_queries.json", default={})
    manifests = sorted(str(path.relative_to(CRAWLER_DIR)) for path in (CRAWLER_DIR / "manifests").glob("*.csv"))

    return {
        "text_rag": {
            "source_count": len(rag.sources()),
            "sources": rag.sources(),
            "chunk_count": _count_json_chunks(CHUNKS_DIR),
            "raw_document_count": _count_files(RAW_DIR, {".json", ".txt", ".pdf", ".docx", ".html", ".htm"}),
            "cleaned_document_count": _count_files(CLEANED_DIR, {".txt"}),
            "recent_crawl_history": crawler.recent_history(limit=30),
            "recent_discovered_links": crawler.recent_links(limit=30),
            "recent_search_candidates": search_discovery.recent_candidates(limit=50),
        },
        "image_crawl": {
            "raw_count_by_class": _count_class_files(IMAGE_DATASET_DIR / "raw"),
            "clean_count_by_class": _count_class_files(IMAGE_DATASET_DIR / "cleaned"),
            "rejected_count_by_reason": _count_rejected(IMAGE_DATASET_DIR / "rejected"),
            "metadata_count": len(image_metadata),
            "download_failure_count": len(download_failures),
            "metadata_preview": image_metadata[:20],
            "download_failures_preview": download_failures[:20],
        },
        "reports": {
            "dataset_summary": _read_csv_file(REPORTS_DIR / "dataset_summary.csv"),
            "source_domain_summary": _read_csv_file(REPORTS_DIR / "source_domain_summary.csv"),
            "rejected_summary": _read_csv_file(REPORTS_DIR / "rejected_summary.csv"),
        },
        "research": {
            "source_registry": source_registry,
            "queries": queries,
            "manifests": manifests,
        },
    }


@router.post("/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, str]:
    log = get_request_logger(payload.request_id)
    log.info("feedback value=%s notes=%s", payload.feedback, payload.notes or "")
    _log_activity(
        payload.request_id,
        "feedback",
        payload.feedback,
        "User feedback received",
        {"feedback": payload.feedback, "notes": payload.notes or ""},
    )
    return {"status": "received", "request_id": payload.request_id}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    """Privacy: let users erase their own session footprint from in-memory activity logs.

    Server only keeps `session_id` (opaque to us) plus event metadata (hashes,
    lengths, source ids). No raw question text is stored, but we still wipe the
    matching rows so a user can fully clear their trace.

    The audit row we leave behind for ops only carries a short hash of the
    session id (not the id itself) so the deletion itself does not re-pin the
    session into the activity log.
    """
    if not session_id or len(session_id) > 128:
        raise HTTPException(status_code=400, detail="Invalid session_id.")
    before = len(ACTIVITY_EVENTS)
    ACTIVITY_EVENTS[:] = [
        event for event in ACTIVITY_EVENTS if (event.get("payload") or {}).get("session_id") != session_id
    ]
    removed = before - len(ACTIVITY_EVENTS)
    _log_activity(
        "system",
        "privacy",
        "session_deleted",
        "User session activity erased",
        {"session_id_hash": _short_hash(session_id), "removed_events": removed},
    )
    return {"status": "deleted", "session_id": session_id, "removed_events": removed}


@router.post("/diagnose-image")
@limiter.limit(DEFAULT_IMAGE_LIMIT)
async def diagnose_image(request: Request, file: UploadFile = File(...)) -> dict:
    request_id = str(uuid4())
    log = get_request_logger(request_id)
    image_bytes = await read_upload_capped(file, MAX_IMAGE_BYTES, "Image")
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image file is empty.")

    quality = validate_image_quality(image_bytes, file.content_type)
    if quality.passed:
        prediction = classifier.predict(image_bytes)
    else:
        prediction = VisionPrediction("unknown", 0.0, ["kiểm tra chất lượng ảnh không đạt"])

    chunks = rag.retrieve_for_label(prediction.disease_label, prediction.observed_symptoms, top_k=4)
    rag_advice = advisor.image_advice(prediction, chunks)
    log.info(
        "image_quality=%s predicted_label=%s confidence=%.2f retrieved_source_ids=%s",
        quality.passed,
        prediction.disease_label,
        prediction.confidence,
        [c["metadata"]["source_id"] for c in chunks],
    )
    _log_activity(
        request_id,
        "image",
        "diagnosed",
        "Image diagnosis request processed",
        {
            "quality_passed": quality.passed,
            "disease_label": prediction.disease_label,
            "confidence": prediction.confidence,
            "retrieved_source_ids": [c["metadata"]["source_id"] for c in chunks],
        },
    )

    return {
        "request_id": request_id,
        "image_quality": {"passed": quality.passed, "issues": quality.issues},
        "prediction": {
            "disease_label": prediction.disease_label,
            "confidence": prediction.confidence,
            "observed_symptoms": prediction.observed_symptoms,
        },
        "rag_advice": rag_advice,
    }
