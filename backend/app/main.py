import csv
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.shared.latency import LatencyMiddleware
from app.shared.rate_limit import limiter


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "message": "Quá nhiều yêu cầu, vui lòng thử lại sau ít phút.",
            "detail": str(exc.detail) if hasattr(exc, "detail") else "rate_limited",
        },
    )


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
    )

    # Rate limiter wiring (process-local; see app.shared.rate_limit for storage notes).
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    application.add_middleware(SlowAPIMiddleware)
    # Latency middleware sits in front of SlowAPI so we still time rate-limited
    # responses (they are real requests too).
    application.add_middleware(LatencyMiddleware)

    # Set all CORS enabled origins
    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Đăng ký các Routers từ Presentation Layers. Chỉ còn module `ml_agri_chat`
    # vận hành thật; các mock module cũ (chat/handbook/diagnostics) đã được gỡ
    # khỏi codebase vì chỉ trả response cứng và dễ gây hiểu lầm.
    try:
        from app.ml_agri_chat.router import router as ml_agri_router
    except ModuleNotFoundError as exc:
        missing_dependency = exc.name
        ml_agri_router = _build_ml_agri_fallback_router(missing_dependency)

    application.include_router(ml_agri_router, prefix=f"{settings.API_V1_STR}/ml-agri", tags=["ML-Agri Chat Admin"])
    return application

async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": "Endpoint không tồn tại hoặc đã bị di dời.",
                "data": None
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": str(exc.detail)}
    )

def health_check():
    return {"status": "ok", "message": "Nông Trí AI Backend is running!"}


def _build_ml_agri_fallback_router(missing_dependency: str) -> APIRouter:
    router = APIRouter()
    base_dir = Path(__file__).resolve().parent / "ml_agri_chat"
    data_dir = base_dir / "data"
    raw_dir = data_dir / "raw_documents"
    cleaned_dir = data_dir / "cleaned_documents"
    chunks_dir = data_dir / "chunks"
    vector_dir = data_dir / "vector_store"
    crawl_candidate_dir = data_dir / "crawl_candidates"
    pipeline_dir = base_dir / "ml_pipeline"
    crawler_dir = pipeline_dir / "crawler"
    image_dataset_dir = pipeline_dir / "dataset"
    reports_dir = pipeline_dir / "reports"

    def runtime_status() -> dict[str, Any]:
        return {
            "status": "degraded",
            "phase": "admin_read_only_fallback",
            "message": (
                "ML-Agri admin is running with read-only local data because a runtime dependency is missing. "
                "Use Docker or recreate backend/.venv with Python 3.11 and install backend/requirements.txt."
            ),
            "missing_dependency": missing_dependency,
            "required_python": "3.11",
            "llm": {"enabled": False, "status": "unavailable"},
        }

    @router.get("/health")
    def ml_agri_health_unavailable():
        return runtime_status()

    @router.get("/sources")
    def sources() -> dict[str, list[dict[str, Any]]]:
        return {"sources": _fallback_sources(vector_dir / "chunks.json", raw_dir)}

    @router.get("/data-quality")
    def data_quality() -> dict[str, Any]:
        source_reports = _fallback_source_quality(raw_dir, cleaned_dir, chunks_dir)
        vector_chunks = _read_json(vector_dir / "chunks.json", [])
        return {
            "summary": {
                "source_count": len(source_reports),
                "chunk_count": sum(item["chunk_count"] for item in source_reports),
                "vector_chunk_count": len(vector_chunks) if isinstance(vector_chunks, list) else 0,
                "avg_quality_score": round(_avg([item["quality_score"] for item in source_reports]), 3),
                "warning_counts": _counter_dict(warning for item in source_reports for warning in item["warnings"]),
                "reliability_counts": _counter_dict(item["reliability_level"] for item in source_reports),
                "source_type_counts": _counter_dict(item["source_type"] for item in source_reports),
            },
            "sources": sorted(source_reports, key=lambda item: (item["quality_score"], -item["cleaned_char_count"])),
            "runtime": runtime_status(),
        }

    @router.get("/trust-report")
    def trust_report() -> dict[str, Any]:
        source_reports = _fallback_source_quality(raw_dir, cleaned_dir, chunks_dir)
        source_count = len(source_reports)
        warning_total = sum(len(item.get("warnings") or []) for item in source_reports)
        reliability = _counter_dict(item.get("reliability_level") for item in source_reports)
        official = int(reliability.get("official") or 0)
        semi_official = int(reliability.get("semi_official") or 0)
        reviewed_share = (official + semi_official) / source_count if source_count else 0
        trust_score = max(0, min(100, 100 - int((1 - reviewed_share) * 35) - min(25, int(warning_total / max(source_count, 1) * 8))))
        return {
            "summary": {
                "trust_score": trust_score,
                "status": "review" if trust_score >= 60 else "high_risk",
                "source_count": source_count,
                "reviewed_source_share": round(reviewed_share, 3),
                "official_source_share": round(official / source_count, 3) if source_count else 0,
                "internet_source_share": round(int(reliability.get("internet") or 0) / source_count, 3) if source_count else 0,
                "warning_total": warning_total,
                "high_risk_warning_total": warning_total,
                "topic_coverage_rate": 0,
                "top_domain_share": 0,
            },
            "coverage": [],
            "region_coverage": [],
            "domain_concentration": [],
            "risk_register": [
                {
                    "key": "runtime",
                    "title": "Backend đang chạy fallback read-only",
                    "severity": "high",
                    "status": "needs_action",
                    "evidence": f"Missing dependency: {missing_dependency}",
                    "mitigation": "Dùng Docker hoặc tạo backend/.venv bằng Python 3.11 và cài requirements.",
                }
            ],
            "controls": [],
            "model_card": {
                "system_name": "Nông Trí AI / ML-Agri-Chat",
                "intended_use": "Admin read-only fallback khi local thiếu dependency.",
            },
            "runtime": runtime_status(),
        }

    @router.get("/crawl-dashboard")
    def crawl_dashboard() -> dict[str, Any]:
        image_metadata = _read_json(image_dataset_dir / "raw" / "metadata.json", [])
        download_failures = _read_json(image_dataset_dir / "raw" / "download_failures.json", [])
        return {
            "text_rag": {
                "source_count": len(_fallback_sources(vector_dir / "chunks.json", raw_dir)),
                "sources": _fallback_sources(vector_dir / "chunks.json", raw_dir),
                "chunk_count": _count_json_chunks(chunks_dir),
                "raw_document_count": _count_files(raw_dir, {".json", ".txt", ".pdf", ".docx", ".html", ".htm"}),
                "cleaned_document_count": _count_files(cleaned_dir, {".txt"}),
                "recent_crawl_history": _read_jsonl(crawl_candidate_dir / "crawl_history.jsonl", 30),
                "recent_discovered_links": _read_jsonl(crawl_candidate_dir / "discovered_links.jsonl", 30),
                "recent_search_candidates": _read_jsonl(crawl_candidate_dir / "search_candidates.jsonl", 50),
            },
            "image_crawl": {
                "raw_count_by_class": _count_class_files(image_dataset_dir / "raw"),
                "clean_count_by_class": _count_class_files(image_dataset_dir / "cleaned"),
                "rejected_count_by_reason": _count_class_files(image_dataset_dir / "rejected"),
                "metadata_count": len(image_metadata) if isinstance(image_metadata, list) else 0,
                "download_failure_count": len(download_failures) if isinstance(download_failures, list) else 0,
                "metadata_preview": image_metadata[:20] if isinstance(image_metadata, list) else [],
                "download_failures_preview": download_failures[:20] if isinstance(download_failures, list) else [],
            },
            "reports": {
                "dataset_summary": _read_csv(reports_dir / "dataset_summary.csv"),
                "source_domain_summary": _read_csv(reports_dir / "source_domain_summary.csv"),
                "rejected_summary": _read_csv(reports_dir / "rejected_summary.csv"),
            },
            "research": {
                "source_registry": _read_json(crawler_dir / "source_registry.json", {}),
                "queries": _read_json(crawler_dir / "search_queries.json", {}),
                "manifests": sorted(str(path.relative_to(crawler_dir)) for path in (crawler_dir / "manifests").glob("*.csv")),
            },
            "runtime": runtime_status(),
        }

    @router.get("/crawl-events")
    def crawl_events(limit: int = 120) -> dict[str, list[dict[str, Any]]]:
        return {"events": _read_jsonl(crawl_candidate_dir / "crawl_history.jsonl", max(1, min(limit, 2000)))}

    @router.get("/admin/ops-events")
    def admin_ops_events(limit: int = 200) -> dict[str, Any]:
        return {
            "events": _read_jsonl(crawl_candidate_dir / "crawl_history.jsonl", max(1, min(limit, 500))),
            "pipelines": [
                {"name": "Backend runtime", "status": "degraded", "detail": f"Missing dependency: {missing_dependency}"},
                {"name": "Admin read API", "status": "ok", "detail": "Serving local JSON/CSV reports"},
            ],
        }

    @router.get("/taxonomy")
    def taxonomy() -> dict[str, list[dict[str, Any]]]:
        return {"categories": []}

    @router.post("/rag-evaluate")
    def rag_evaluate() -> dict[str, Any]:
        return {"summary": {"case_count": 0, "passed": 0, "failed": 0, "pass_rate": 0}, "results": [], "runtime": runtime_status()}

    @router.post("/rag-rebuild-index")
    def rag_rebuild_index() -> dict[str, Any]:
        return {"status": "skipped", "reason": f"Missing dependency: {missing_dependency}", "chunks_indexed": 0}

    @router.post("/chat")
    def chat() -> dict[str, Any]:
        return {
            "answer": "Backend ML-Agri đang chạy chế độ read-only vì thiếu dependency runtime trong .venv local.",
            "sources": [],
            "confidence_level": "thap",
            "runtime": runtime_status(),
        }

    @router.post("/research-search")
    def research_search() -> dict[str, Any]:
        return {"query": "", "candidates": [], "events": [], "runtime": runtime_status()}

    @router.post("/research-batch")
    def research_batch() -> dict[str, Any]:
        return {"results": [], "events": [], "runtime": runtime_status()}

    @router.post("/crawl-urls")
    def crawl_urls() -> dict[str, Any]:
        return {"status": "skipped", "results": [], "runtime": runtime_status()}

    return router


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def _fallback_sources(vector_path: Path, raw_dir: Path) -> list[dict[str, Any]]:
    chunks = _read_json(vector_path, [])
    sources: dict[str, dict[str, Any]] = {}
    if isinstance(chunks, list):
        for chunk in chunks:
            metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else {}
            source_id = metadata.get("source_id")
            if not source_id or source_id in sources:
                continue
            sources[source_id] = {
                "source_id": source_id,
                "title": metadata.get("title") or metadata.get("file_name") or source_id,
                "url": metadata.get("url"),
                "file_name": metadata.get("file_name"),
                "source_type": metadata.get("source_type") or "unknown",
                "reliability_level": metadata.get("reliability_level") or "unknown",
                "category": metadata.get("category"),
                "category_label": metadata.get("category_label"),
            }
    for raw_path in raw_dir.glob("*.json"):
        raw_payload = _read_json(raw_path, {})
        metadata = raw_payload.get("metadata", {}) if isinstance(raw_payload, dict) else {}
        source_id = metadata.get("source_id") or raw_path.stem
        sources.setdefault(
            source_id,
            {
                "source_id": source_id,
                "title": metadata.get("title") or metadata.get("file_name") or source_id,
                "url": metadata.get("url"),
                "file_name": metadata.get("file_name"),
                "source_type": metadata.get("source_type") or "unknown",
                "reliability_level": metadata.get("reliability_level") or "unknown",
            },
        )
    return sorted(sources.values(), key=lambda item: item.get("title") or item["source_id"])


def _fallback_source_quality(raw_dir: Path, cleaned_dir: Path, chunks_dir: Path) -> list[dict[str, Any]]:
    reports = []
    for raw_path in sorted(raw_dir.glob("*.json")):
        raw_payload = _read_json(raw_path, {})
        metadata = raw_payload.get("metadata", {}) if isinstance(raw_payload, dict) else {}
        source_id = metadata.get("source_id") or raw_path.stem
        raw_text = raw_payload.get("raw_text") or ""
        cleaned_text = _safe_read_text(cleaned_dir / f"{source_id}.txt")
        chunks = _read_json(chunks_dir / f"{source_id}.json", [])
        warnings = []
        if len(cleaned_text) < 500:
            warnings.append("cleaned_text_too_short")
        if not metadata.get("url") and not metadata.get("file_name"):
            warnings.append("missing_source_locator")
        reliability = metadata.get("reliability_level") or "unknown"
        if reliability == "internet":
            warnings.append("internet_source_needs_review")
        quality_score = max(0.0, 1.0 - min(0.5, len(warnings) * 0.1) - (0.2 if reliability == "internet" else 0.0))
        reports.append(
            {
                "source_id": source_id,
                "title": metadata.get("title"),
                "url": metadata.get("url"),
                "file_name": metadata.get("file_name"),
                "source_type": metadata.get("source_type") or "unknown",
                "reliability_level": reliability,
                "category": metadata.get("category"),
                "category_label": metadata.get("category_label"),
                "raw_char_count": len(raw_text),
                "cleaned_char_count": len(cleaned_text),
                "chunk_count": len(chunks) if isinstance(chunks, list) else 0,
                "avg_chunk_chars": round(_avg([len(chunk.get("text", "")) for chunk in chunks]), 1) if isinstance(chunks, list) else 0,
                "duplicate_line_ratio": 0,
                "noise_line_ratio": 0,
                "vietnamese_signal_ratio": 0,
                "quality_score": round(quality_score, 3),
                "warnings": warnings,
            }
        )
    return reports


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError:
        return ""


def _count_files(directory: Path, suffixes: set[str]) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.iterdir() if path.is_file() and path.suffix.lower() in suffixes)


def _count_json_chunks(directory: Path) -> int:
    total = 0
    for path in directory.glob("*.json"):
        payload = _read_json(path, [])
        if isinstance(payload, list):
            total += len(payload)
    return total


def _count_class_files(directory: Path) -> dict[str, int]:
    if not directory.exists():
        return {}
    return {
        path.name: sum(1 for child in path.rglob("*") if child.is_file())
        for path in directory.iterdir()
        if path.is_dir()
    }


def _counter_dict(items) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _avg(values: "list[int | float]") -> float:
    return sum(values) / len(values) if values else 0.0


app = get_application()
app.add_exception_handler(StarletteHTTPException, custom_http_exception_handler)
app.get("/health")(health_check)
