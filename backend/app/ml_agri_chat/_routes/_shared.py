"""Shared state, paths, singletons, and Pydantic models for the
ml_agri_chat routes.

Splitting `router.py` (1300+ lines) into per-domain modules is only safe
if every endpoint module agrees on the same instances of the RAG store,
the advisor, the crawler, the activity ring buffers, etc. This module is
the single source of those singletons - no submodule allocates its own
copy. The package-level `router.py` still exposes the FastAPI `router`
object that `app/main.py` mounts; the submodules under `_routes/` reach
in here to read state and attach their endpoints to that router.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.ml_agri_chat.modules.data_ingestion import DataIngestor
from app.ml_agri_chat.modules.internet_crawler import InternetCrawler
from app.ml_agri_chat.modules.intent_classifier import CascadeIntentClassifier
from app.ml_agri_chat.modules.llm_advisor import ControlledAdvisor
from app.ml_agri_chat.modules.rag import AgriculturalRAG
from app.ml_agri_chat.modules.search_discovery import SearchDiscovery
from app.ml_agri_chat.modules.vision_model import CoffeeVisionClassifier
from app.shared.upload import max_document_bytes, max_image_bytes


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
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


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

ingestor = DataIngestor(RAW_DIR)
crawler = InternetCrawler(ingestor, CRAWL_CANDIDATE_DIR)
search_discovery = SearchDiscovery(CRAWL_CANDIDATE_DIR)
rag = AgriculturalRAG(VECTOR_DIR)
advisor = ControlledAdvisor()
intent_classifier = CascadeIntentClassifier(advisor.llm_client)
vision_classifier = CoffeeVisionClassifier(ML_PIPELINE_DIR / "models" / "coffee_disease_model.keras")


# ---------------------------------------------------------------------------
# Ring buffers + caps
# ---------------------------------------------------------------------------

CRAWL_EVENTS: list[dict] = []
ACTIVITY_EVENTS: list[dict] = []

# In-memory event ring buffers — capped to prevent memory leak (see audit C10).
MAX_CRAWL_EVENTS = int(os.getenv("NONGTRI_MAX_CRAWL_EVENTS", "500"))
MAX_ACTIVITY_EVENTS = int(os.getenv("NONGTRI_MAX_ACTIVITY_EVENTS", "1000"))

# Upload size limits resolved once at import; tweak via env vars.
MAX_IMAGE_BYTES = max_image_bytes()
MAX_DOCUMENT_BYTES = max_document_bytes()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---------------------------------------------------------------------------
# Auth + small helpers shared by every domain module
# ---------------------------------------------------------------------------


def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """Simple admin auth via shared secret in `X-Admin-Token` header.

    If `NONGTRI_ADMIN_TOKEN` is unset, admin endpoints are disabled
    (return 503) to fail closed by default. Set it in env to enable.
    """
    expected = os.getenv("NONGTRI_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin endpoints are disabled (NONGTRI_ADMIN_TOKEN unset).")
    if not x_admin_token or x_admin_token.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Token.")


def short_hash(value: str) -> str:
    """Short fingerprint for log correlation without exposing content."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def log_activity(
    request_id: str,
    stream: str,
    event: str,
    message: str,
    payload: dict | None = None,
) -> None:
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


def log_crawl_event(request_id: str, event: dict) -> None:
    CRAWL_EVENTS.append(
        {
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            **event,
        }
    )
    log_activity(
        request_id,
        "crawl",
        str(event.get("event") or event.get("status") or "event"),
        event.get("title") or event.get("url") or event.get("source_id") or "Crawler event",
        {key: value for key, value in event.items() if key not in {"title"}},
    )
    if len(CRAWL_EVENTS) > MAX_CRAWL_EVENTS:
        del CRAWL_EVENTS[: len(CRAWL_EVENTS) - MAX_CRAWL_EVENTS]


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


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
    # When `True`, the crawler bypasses duplicate detection on already-stored
    # raw documents and overwrites them with the freshly fetched content.
    # The previous raw file is backed up to <source_id>.json.bak so a bad
    # refresh can be rolled back. Defaults to False so the historical
    # "skip if already crawled" UX is the safe default.
    force: bool = False


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
