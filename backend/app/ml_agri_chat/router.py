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
from app.ml_agri_chat.modules.llm_advisor import ControlledAdvisor
from app.ml_agri_chat.modules.logger import get_request_logger
from app.ml_agri_chat.modules.prompt_guard import DISCLAIMER, basic_chat_response, validate_question
from app.ml_agri_chat.modules.rag import AgriculturalRAG
from app.ml_agri_chat.modules.search_discovery import SearchDiscovery
from app.ml_agri_chat.modules.source_policy import source_review_decision, source_warnings
from app.ml_agri_chat.modules.taxonomy import CATEGORY_MAP, classify_query, enrich_metadata_with_taxonomy, is_vague_disease_question, taxonomy_payload
from app.ml_agri_chat.modules.text_cleaning import clean_text
from app.ml_agri_chat.modules.vision_model import CoffeeVisionClassifier, VisionPrediction
from app.shared.rate_limit import (
    DEFAULT_ADMIN_LIMIT,
    DEFAULT_CHAT_LIMIT,
    DEFAULT_IMAGE_LIMIT,
    limiter,
)
from app.shared.upload import max_document_bytes, max_image_bytes, read_upload_capped


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw_documents"
CLEANED_DIR = DATA_DIR / "cleaned_documents"
CHUNKS_DIR = DATA_DIR / "chunks"
VECTOR_DIR = DATA_DIR / "vector_store"
KB_DIR = DATA_DIR / "knowledge_base"
CRAWL_CANDIDATE_DIR = DATA_DIR / "crawl_candidates"
EVALUATION_DIR = DATA_DIR / "evaluation"
ML_PIPELINE_DIR = BASE_DIR / "ml_pipeline"
CRAWLER_DIR = ML_PIPELINE_DIR / "crawler"
IMAGE_DATASET_DIR = ML_PIPELINE_DIR / "dataset"
REPORTS_DIR = ML_PIPELINE_DIR / "reports"

for directory in [RAW_DIR, CLEANED_DIR, CHUNKS_DIR, VECTOR_DIR, KB_DIR, CRAWL_CANDIDATE_DIR, EVALUATION_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

ingestor = DataIngestor(RAW_DIR)
crawler = InternetCrawler(ingestor, CRAWL_CANDIDATE_DIR)
search_discovery = SearchDiscovery(CRAWL_CANDIDATE_DIR)
rag = AgriculturalRAG(VECTOR_DIR)
advisor = ControlledAdvisor()
classifier = CoffeeVisionClassifier(ML_PIPELINE_DIR / "models" / "coffee_disease_model.keras")
CRAWL_EVENTS: list[dict] = []
ACTIVITY_EVENTS: list[dict] = []

# In-memory event ring buffers — capped to prevent memory leak (see audit C10).
MAX_CRAWL_EVENTS = int(os.getenv("NONGTRI_MAX_CRAWL_EVENTS", "500"))
MAX_ACTIVITY_EVENTS = int(os.getenv("NONGTRI_MAX_ACTIVITY_EVENTS", "1000"))

# Upload size limits resolved once at import; tweak via env vars.
MAX_IMAGE_BYTES = max_image_bytes()
MAX_DOCUMENT_BYTES = max_document_bytes()

router = APIRouter()


def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """Simple admin auth via shared secret in `X-Admin-Token` header.

    If `NONGTRI_ADMIN_TOKEN` is unset, admin endpoints are disabled (return 503)
    to fail closed by default. Set it in env to enable.
    """
    expected = os.getenv("NONGTRI_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin endpoints are disabled (NONGTRI_ADMIN_TOKEN unset).")
    if not x_admin_token or x_admin_token.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Token.")


def _short_hash(value: str) -> str:
    """Return a short fingerprint for log correlation without exposing content."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


class ChatHistoryMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|ai)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2)
    top_k: int = Field(default=5, ge=1, le=10)
    session_id: Optional[str] = None
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=12)


class IngestUrlRequest(BaseModel):
    url: str
    title: Optional[str] = None
    reliability_level: str = Field(default="internet", pattern="^(official|semi_official|internet|manual)$")


class CrawlUrlsRequest(BaseModel):
    urls: list[str] = Field(min_length=1)
    reliability_level: str = Field(default="internet", pattern="^(official|semi_official|internet|manual)$")
    max_pages: int = Field(default=10, ge=1)
    collect_links: bool = False
    same_domain_only: bool = True


class ResearchSearchRequest(BaseModel):
    query: str = Field(min_length=2)
    max_results: int = Field(default=50, ge=1, le=500)
    auto_crawl: bool = False
    crawl_top_k: int = Field(default=3, ge=1, le=10)


class ResearchBatchRequest(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=100)
    max_results: int = Field(default=50, ge=1, le=500)
    target_per_query: int = Field(default=6, ge=1, le=20)


class FeedbackRequest(BaseModel):
    request_id: str
    feedback: str = Field(pattern="^(correct|incorrect|unclear)$")
    notes: Optional[str] = None


class RagEvaluateRequest(BaseModel):
    top_k: int = Field(default=5, ge=1, le=10)


class ResetDataRequest(BaseModel):
    seed_knowledge_base: bool = False


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
    current = " ".join(question.split())
    lowered = current.lower()
    followup_markers = (
        "ngoài ra",
        "vậy",
        "thế",
        "còn",
        "cần thêm",
        "bổ sung",
        "nữa",
        "tiếp",
        "ý đó",
        "như trên",
    )
    is_followup = len(current) < 120 and any(marker in lowered for marker in followup_markers)
    if not is_followup:
        return current
    previous_user = next((item["content"] for item in reversed(history) if item["role"] == "user"), "")
    previous_assistant = next((item["content"] for item in reversed(history) if item["role"] == "assistant"), "")
    context = previous_user or previous_assistant
    if not context:
        return current
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
    if any(term in lowered for term in concrete_terms):
        return f"{current}\nNgữ cảnh hội thoại: cây cà phê."
    return f"{current}\nNgữ cảnh hội thoại trước đó: {context}"


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

    basic_response = basic_chat_response(payload.question)
    if basic_response:
        log.info("chat_basic_intent confidence=%s", basic_response["confidence_level"])
        _log_activity(
            request_id,
            "chat",
            "basic_intent",
            "Answered with basic communication intent",
            {"confidence_level": basic_response["confidence_level"]},
        )
        return {
            **basic_response,
            "sources": [],
            "safety_disclaimer": DISCLAIMER,
        }

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
    chunks = rag.retrieve(effective_question, top_k=payload.top_k, category_key=route["category"])
    answer = advisor.answer_chat(payload.question, chunks, history=conversation_history, effective_question=effective_question)
    log.info("chat retrieved_source_ids=%s", [c["metadata"]["source_id"] for c in chunks])
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
    )

    ingested = []
    for item in results:
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
            _log_activity(
                request_id,
                "chunking",
                "duplicate_skipped",
                "Crawled source already exists; skipped chunk/vector write",
                {"source_id": item.source_id, "url": item.url},
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
        "crawl_urls urls=%s ingested=%s failed=%s",
        len(payload.urls),
        sum(1 for item in results if item.status == "ingested"),
        sum(1 for item in results if item.status == "failed"),
    )
    _log_activity(
        request_id,
        "crawl",
        "completed",
        "Manual crawl completed",
        {
            "url_count": len(payload.urls),
            "ingested": sum(1 for item in results if item.status == "ingested"),
            "failed": sum(1 for item in results if item.status == "failed"),
        },
    )
    return {
        "request_id": request_id,
        "results": [item.to_dict() for item in results],
        "ingested": ingested,
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
        {"session_id": session_id, "removed_events": removed},
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


def _clean_chunk_store(source_id: str, raw_text: str, metadata: dict) -> dict:
    cleaned = clean_text(raw_text)
    with (CLEANED_DIR / f"{source_id}.txt").open("w", encoding="utf-8") as handle:
        handle.write(cleaned)

    enriched_metadata = enrich_metadata_with_taxonomy(metadata, cleaned)
    warnings = _indexing_warnings(enriched_metadata, raw_text, cleaned)
    quality_score = _indexing_quality_score(enriched_metadata, raw_text, cleaned, warnings)
    review = source_review_decision(enriched_metadata, quality_score, warnings)
    enriched_metadata.update(
        {
            "quality_score": round(quality_score, 3),
            "warnings": warnings,
            **review,
        }
    )
    chunks = chunk_document(cleaned, enriched_metadata)
    chunk_dicts = [chunk.to_dict() for chunk in chunks]
    with (CHUNKS_DIR / f"{source_id}.json").open("w", encoding="utf-8") as handle:
        json.dump(chunk_dicts, handle, ensure_ascii=False, indent=2)

    added = 0
    if review["indexing_status"] == "indexed":
        added = rag.add_chunks(chunk_dicts)
    return {
        "status": "ingested",
        "source_id": source_id,
        "chunks_created": len(chunks),
        "chunks_added": added,
        "review_status": review["review_status"],
        "indexing_status": review["indexing_status"],
        "quality_score": round(quality_score, 3),
        "warnings": warnings,
    }


def _indexing_warnings(metadata: dict, raw_text: str, cleaned: str) -> list[str]:
    warnings = []
    if len(cleaned) < 500:
        warnings.append("cleaned_text_too_short")
    if len(raw_text) > 0 and len(cleaned) / len(raw_text) < 0.15:
        warnings.append("too_much_text_removed")
    warnings.extend(source_warnings(metadata.get("title"), metadata.get("url"), cleaned))
    return list(dict.fromkeys(warnings))


def _indexing_quality_score(metadata: dict, raw_text: str, cleaned: str, warnings: list[str]) -> float:
    reliability = metadata.get("reliability_level") or "internet"
    score = 1.0
    score -= {"official": 0.0, "semi_official": 0.08, "manual": 0.05, "internet": 0.22}.get(reliability, 0.22)
    score -= min(0.5, len(warnings) * 0.08)
    if len(cleaned) < 500:
        score -= 0.18
    if len(raw_text) > 0 and len(cleaned) / len(raw_text) < 0.15:
        score -= 0.12
    return max(0.0, min(1.0, score))


def _chunks_for_trusted_rebuild(source_id: str, chunks: object) -> tuple[list[dict], dict]:
    if not isinstance(chunks, list) or not chunks:
        return [], {"indexing_status": "held_for_review", "review_status": "needs_review"}
    valid_chunks = [chunk for chunk in chunks if isinstance(chunk, dict)]
    if not valid_chunks:
        return [], {"indexing_status": "held_for_review", "review_status": "needs_review"}

    metadata = dict(valid_chunks[0].get("metadata") or {})
    if metadata.get("indexing_status") == "indexed" or metadata.get("review_status") == "approved":
        return valid_chunks, {"indexing_status": "indexed", "review_status": "approved"}
    if metadata.get("indexing_status") == "blocked" or metadata.get("review_status") == "rejected":
        return [], {"indexing_status": "blocked", "review_status": "rejected"}
    if metadata.get("indexing_status") == "held_for_review" or metadata.get("review_status") == "needs_review":
        return [], {"indexing_status": "held_for_review", "review_status": "needs_review"}

    joined_text = "\n".join(str(chunk.get("text") or "") for chunk in valid_chunks)
    warnings = _indexing_warnings(metadata, "", joined_text)
    quality_score = _indexing_quality_score(metadata, "", joined_text, warnings)
    decision = source_review_decision(metadata, quality_score, warnings)
    if decision["indexing_status"] != "indexed":
        return [], decision

    enriched_chunks = []
    for chunk in valid_chunks:
        chunk_copy = dict(chunk)
        chunk_metadata = dict(chunk_copy.get("metadata") or {})
        chunk_metadata.update(
            {
                "source_id": chunk_metadata.get("source_id") or source_id,
                "quality_score": round(quality_score, 3),
                "warnings": warnings,
                **decision,
            }
        )
        chunk_copy["metadata"] = chunk_metadata
        enriched_chunks.append(chunk_copy)
    return enriched_chunks, decision


def _duplicate_result(ingested: IngestedDocument) -> dict:
    return {
        "status": "duplicate",
        "source_id": ingested.source_id,
        "duplicate_of": ingested.duplicate_of or ingested.source_id,
        "chunks_created": _existing_chunk_count(ingested.source_id),
        "chunks_added": 0,
        "message": "Source already exists; skipped raw/chunk/vector write.",
    }


def _existing_chunk_count(source_id: str) -> int:
    chunks = _read_json_file(CHUNKS_DIR / f"{source_id}.json", default=[])
    return len(chunks) if isinstance(chunks, list) else 0


def _seed_knowledge_base_if_needed() -> None:
    if rag.sources():
        return
    for path in sorted(KB_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            item = json.load(handle)
        metadata = {
            "source_id": path.stem,
            "source_type": item.get("source_type", "manual"),
            "title": item.get("title", path.stem),
            "file_name": path.name,
            "url": None,
            "page": None,
            "reliability_level": item.get("reliability_level", "manual"),
            "seed_sample": True,
        }
        _clean_chunk_store(path.stem, item.get("text", ""), metadata)


def _ensure_taxonomy_labels() -> None:
    changed = False
    chunk_dicts: list[dict] = []
    for path in sorted(CHUNKS_DIR.glob("*.json")):
        chunks = _read_json_file(path, default=[])
        if not isinstance(chunks, list):
            continue
        file_changed = False
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            if not metadata.get("category"):
                enriched = enrich_metadata_with_taxonomy(metadata, chunk.get("text", ""))
                chunk["metadata"] = enriched
                file_changed = True
        if file_changed:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(chunks, handle, ensure_ascii=False, indent=2)
            changed = True
        indexable, _decision = _chunks_for_trusted_rebuild(path.stem, chunks)
        chunk_dicts.extend(indexable)
    if changed and chunk_dicts:
        rag.rebuild(chunk_dicts)


def _read_json_file(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _count_files(root: Path, suffixes: set[str]) -> int:
    if not root.exists():
        return 0
    return sum(1 for item in root.rglob("*") if item.is_file() and item.suffix.lower() in suffixes)


def _count_json_chunks(root: Path) -> int:
    total = 0
    for path in root.glob("*.json"):
        data = _read_json_file(path, default=[])
        if isinstance(data, list):
            total += len(data)
    return total


def _chunk_previews(path: Path) -> list[dict]:
    chunks = _read_json_file(path, default=[])
    if not isinstance(chunks, list):
        return []
    return [
        {
            "chunk_id": chunk.get("chunk_id"),
            "text": (chunk.get("text") or "")[:900],
            "char_count": len(chunk.get("text") or ""),
        }
        for chunk in chunks[:12]
    ]


def _count_class_files(root: Path) -> dict[str, int]:
    if not root.exists():
        return {}
    counts: dict[str, int] = {}
    for class_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        counts[class_dir.name] = sum(1 for item in class_dir.rglob("*") if item.is_file() and item.name != ".gitkeep")
    return counts


def _count_rejected(root: Path) -> dict[str, int]:
    if not root.exists():
        return {}
    counts: dict[str, int] = {}
    for reason_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        counts[reason_dir.name] = sum(1 for item in reason_dir.rglob("*") if item.is_file())
    return counts


def _clear_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.name == ".gitkeep":
            continue
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            _clear_directory(path)
            path.rmdir()


def _log_crawl_event(request_id: str, event: dict) -> None:
    CRAWL_EVENTS.append(
        {
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            **event,
        }
    )
    _log_activity(
        request_id,
        "crawl",
        str(event.get("event") or event.get("status") or "event"),
        event.get("title") or event.get("url") or event.get("source_id") or "Crawler event",
        {key: value for key, value in event.items() if key not in {"title"}},
    )
    if len(CRAWL_EVENTS) > MAX_CRAWL_EVENTS:
        del CRAWL_EVENTS[: len(CRAWL_EVENTS) - MAX_CRAWL_EVENTS]


def _log_activity(request_id: str, stream: str, event: str, message: str, payload: dict | None = None) -> None:
    ACTIVITY_EVENTS.append(
        {
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "stream": stream,
            "event": event,
            "message": message,
            "payload": payload or {},
        }
    )
    if len(ACTIVITY_EVENTS) > MAX_ACTIVITY_EVENTS:
        del ACTIVITY_EVENTS[: len(ACTIVITY_EVENTS) - MAX_ACTIVITY_EVENTS]


def _ops_pipeline_status() -> dict:
    raw_docs = _count_files(RAW_DIR, {".json", ".txt", ".pdf", ".docx", ".html", ".htm"})
    cleaned_docs = _count_files(CLEANED_DIR, {".txt"})
    chunk_files = len(list(CHUNKS_DIR.glob("*.json")))
    chunk_count = _count_json_chunks(CHUNKS_DIR)
    vector_chunks = len(_read_json_file(VECTOR_DIR / "chunks.json", default=[]))
    raw_images = sum(_count_class_files(IMAGE_DATASET_DIR / "raw").values())
    clean_images = sum(_count_class_files(IMAGE_DATASET_DIR / "cleaned").values())
    rejected_images = sum(_count_rejected(IMAGE_DATASET_DIR / "rejected").values())
    model_path = ML_PIPELINE_DIR / "models" / "coffee_disease_model.keras"
    label_map_path = ML_PIPELINE_DIR / "models" / "label_map.json"
    return {
        "rag_chunking": [
            {"step": "raw_documents", "label": "Raw documents", "count": raw_docs, "status": "done" if raw_docs else "waiting"},
            {"step": "cleaned_documents", "label": "Cleaned text", "count": cleaned_docs, "status": "done" if cleaned_docs else "waiting"},
            {"step": "chunk_files", "label": "Chunk files", "count": chunk_files, "status": "done" if chunk_files else "waiting"},
            {"step": "vector_chunks", "label": "Vector chunks", "count": vector_chunks, "status": "done" if vector_chunks else "waiting"},
        ],
        "vision_training": [
            {"step": "raw_images", "label": "Raw images", "count": raw_images, "status": "done" if raw_images else "waiting"},
            {"step": "clean_images", "label": "Cleaned images", "count": clean_images, "status": "done" if clean_images else "waiting"},
            {"step": "rejected_images", "label": "Rejected images", "count": rejected_images, "status": "review" if rejected_images else "waiting"},
            {"step": "model_export", "label": "Model artifact", "count": int(model_path.exists()), "status": "done" if model_path.exists() and label_map_path.exists() else "placeholder"},
        ],
    }
