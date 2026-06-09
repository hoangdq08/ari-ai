"""Coverage E2E for the remaining ML-Agri endpoints.

Goal: every router endpoint gets at least one happy-path test plus its main
failure modes. Together with `test_e2e_flows.py` and
`test_security_and_privacy.py` this should pin the public API contract.

Where an endpoint reaches out to the network (ingest-url, crawl-urls,
research-*), we stub `requests.get` so the test stays hermetic.
"""

from __future__ import annotations

import importlib
import uuid
from io import BytesIO

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.middleware import SlowAPIMiddleware


# ---------------------------------------------------------------------------
# Reuse the booting helper from test_e2e_flows so behaviour stays identical.
# ---------------------------------------------------------------------------

def _boot_app(monkeypatch, **env: str):
    monkeypatch.setenv("NONGTRI_LLM_ENABLED", "false")
    monkeypatch.setenv("NONGTRI_RATE_LIMIT_CHAT", "1000/minute")
    monkeypatch.setenv("NONGTRI_RATE_LIMIT_IMAGE", "1000/minute")
    monkeypatch.setenv("NONGTRI_RATE_LIMIT_ADMIN", "1000/minute")
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    import app.shared.upload as upload_mod
    import app.shared.rate_limit as rl_mod
    importlib.reload(upload_mod)
    importlib.reload(rl_mod)
    import app.ml_agri_chat.router as router_mod
    importlib.reload(router_mod)

    app = FastAPI()
    app.state.limiter = rl_mod.limiter
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(router_mod.router, prefix="/api/v1/ml-agri")
    return TestClient(app), router_mod


ADMIN_HEADERS = {"X-Admin-Token": "secret-token"}


# ---------------------------------------------------------------------------
# 1. Health
# ---------------------------------------------------------------------------

def test_health_endpoint(monkeypatch):
    client, _ = _boot_app(monkeypatch)
    r = client.get("/api/v1/ml-agri/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert "phase" in body


# ---------------------------------------------------------------------------
# 2. Taxonomy
# ---------------------------------------------------------------------------

def test_taxonomy_returns_category_list(monkeypatch):
    client, _ = _boot_app(monkeypatch)
    r = client.get("/api/v1/ml-agri/taxonomy")
    assert r.status_code == 200
    body = r.json()
    assert "categories" in body
    cats = body["categories"]
    assert isinstance(cats, list) and cats, "Expected at least one category"
    sample = cats[0]
    assert "key" in sample and "label" in sample


# ---------------------------------------------------------------------------
# 3. Data quality + 4. Trust report
# ---------------------------------------------------------------------------

def test_data_quality_report_structure(monkeypatch):
    client, _ = _boot_app(monkeypatch)
    r = client.get("/api/v1/ml-agri/data-quality")
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body
    summary = body["summary"]
    for key in ("source_count", "chunk_count", "vector_chunk_count"):
        assert key in summary


def test_trust_report_structure(monkeypatch):
    client, _ = _boot_app(monkeypatch)
    r = client.get("/api/v1/ml-agri/trust-report")
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body
    summary = body["summary"]
    # Trust score must be inside [0,100].
    score = summary.get("trust_score")
    assert isinstance(score, int) and 0 <= score <= 100


# ---------------------------------------------------------------------------
# 5. Crawl events + 6. Crawl dashboard
# ---------------------------------------------------------------------------

def test_crawl_events_returns_list(monkeypatch):
    client, _ = _boot_app(monkeypatch)
    r = client.get("/api/v1/ml-agri/crawl-events?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "events" in body and isinstance(body["events"], list)
    assert len(body["events"]) <= 5


def test_crawl_dashboard_aggregates_sections(monkeypatch):
    client, _ = _boot_app(monkeypatch)
    r = client.get("/api/v1/ml-agri/crawl-dashboard")
    assert r.status_code == 200
    body = r.json()
    for key in ("text_rag", "image_crawl", "reports", "research"):
        assert key in body


# ---------------------------------------------------------------------------
# 7. Feedback
# ---------------------------------------------------------------------------

def test_feedback_accepts_known_enum(monkeypatch):
    client, router_mod = _boot_app(monkeypatch)
    router_mod.ACTIVITY_EVENTS.clear()
    request_id = str(uuid.uuid4())
    r = client.post(
        "/api/v1/ml-agri/feedback",
        json={"request_id": request_id, "feedback": "correct", "notes": "ok"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "received"
    # An activity row should have been appended.
    assert any(ev.get("stream") == "feedback" for ev in router_mod.ACTIVITY_EVENTS)


def test_feedback_rejects_unknown_enum(monkeypatch):
    client, _ = _boot_app(monkeypatch)
    r = client.post(
        "/api/v1/ml-agri/feedback",
        json={"request_id": "abc", "feedback": "amazing", "notes": ""},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 8. RAG evaluate (uses committed evaluation fixture).
# ---------------------------------------------------------------------------

def test_rag_evaluate_returns_summary(monkeypatch):
    client, _ = _boot_app(monkeypatch)
    r = client.post("/api/v1/ml-agri/rag-evaluate", json={"top_k": 3})
    # The repo ships an eval fixture; if it is empty for any reason we accept
    # the documented 400 instead of crashing.
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        body = r.json()
        assert "summary" in body or "results" in body


# ---------------------------------------------------------------------------
# 9. Admin: RAG rebuild + 10. Reset (after rebuild we restore by re-seeding).
# ---------------------------------------------------------------------------

def test_admin_rag_rebuild_index_requires_token(monkeypatch):
    client, _ = _boot_app(monkeypatch, NONGTRI_ADMIN_TOKEN="secret-token")
    # Unauthorised first.
    r = client.post("/api/v1/ml-agri/rag-rebuild-index")
    assert r.status_code == 401
    # Authorised path returns counts.
    r = client.post("/api/v1/ml-agri/rag-rebuild-index", headers=ADMIN_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "chunks_indexed" in body


def test_admin_reset_then_reseed_keeps_endpoints_healthy(monkeypatch):
    """Calls /admin/reset-rag-data with seed_knowledge_base=True so the
    on-disk fixture is rebuilt to the seeded baseline rather than wiped to
    zero. After reset, /sources must still answer 200."""
    client, _ = _boot_app(monkeypatch, NONGTRI_ADMIN_TOKEN="secret-token")
    r = client.post(
        "/api/v1/ml-agri/admin/reset-rag-data",
        json={"seed_knowledge_base": True},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "reset"
    # Sources should still be reachable; count is whatever the seed yields.
    r = client.get("/api/v1/ml-agri/sources")
    assert r.status_code == 200
    assert "sources" in r.json()


# ---------------------------------------------------------------------------
# 11. Admin: ingest-document (with a tiny inline text file).
# ---------------------------------------------------------------------------

def test_admin_ingest_document_with_plain_text(monkeypatch):
    client, _ = _boot_app(monkeypatch, NONGTRI_ADMIN_TOKEN="secret-token")
    # Tiny but non-empty txt payload to satisfy ingest pipeline.
    payload = (
        "Tài liệu thử nghiệm hướng dẫn bón phân cho cà phê vối tại Tây Nguyên. "
        * 20
    ).encode("utf-8")
    files = {"file": ("test_note.txt", payload, "text/plain")}
    data = {
        "source_type": "manual",
        "title": "Ghi chú thử nghiệm",
        "reliability_level": "manual",
    }
    r = client.post(
        "/api/v1/ml-agri/ingest-document",
        files=files,
        data=data,
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "source_id" in body
    assert body["status"] in {"ingested", "duplicate"}


def test_admin_ingest_document_rejects_empty_file(monkeypatch):
    client, _ = _boot_app(monkeypatch, NONGTRI_ADMIN_TOKEN="secret-token")
    files = {"file": ("empty.txt", b"", "text/plain")}
    data = {"source_type": "manual", "reliability_level": "manual"}
    r = client.post(
        "/api/v1/ml-agri/ingest-document",
        files=files,
        data=data,
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 400


def test_admin_ingest_document_rejects_bad_reliability_level(monkeypatch):
    client, _ = _boot_app(monkeypatch, NONGTRI_ADMIN_TOKEN="secret-token")
    files = {"file": ("note.txt", b"abc xyz", "text/plain")}
    data = {"source_type": "manual", "reliability_level": "GARBAGE"}
    r = client.post(
        "/api/v1/ml-agri/ingest-document",
        files=files,
        data=data,
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 12. Admin: ingest-url (network stubbed).
# ---------------------------------------------------------------------------

class _FakeHttpResponse:
    def __init__(self, body: bytes, status: int = 200, content_type: str = "text/html"):
        self.status_code = status
        self.content = body
        self.text = body.decode("utf-8", errors="ignore")
        self.headers = {"Content-Type": content_type}
        self.url = "https://example.test/article"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def stub_requests(monkeypatch):
    html_body = (
        "<html><head><title>Hướng dẫn cà phê Tây Nguyên</title></head>"
        "<body>" + ("<p>Cà phê cần che bóng và bón phân định kỳ. Triệu chứng vàng lá.</p>" * 30) +
        "</body></html>"
    ).encode("utf-8")

    def fake_get(url, *args, **kwargs):
        return _FakeHttpResponse(html_body)

    import requests
    monkeypatch.setattr(requests, "get", fake_get)
    yield


def test_admin_ingest_url_with_stubbed_network(monkeypatch, stub_requests):
    client, _ = _boot_app(monkeypatch, NONGTRI_ADMIN_TOKEN="secret-token")
    r = client.post(
        "/api/v1/ml-agri/ingest-url",
        json={
            "url": "https://example.test/article",
            "title": "Hướng dẫn cà phê",
            "reliability_level": "internet",
        },
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") in {"ingested", "duplicate"}
    assert "source_id" in body


# ---------------------------------------------------------------------------
# 13. Admin: crawl-urls (also network stubbed).
# ---------------------------------------------------------------------------

def test_admin_crawl_urls_with_stubbed_network(monkeypatch, stub_requests):
    client, _ = _boot_app(monkeypatch, NONGTRI_ADMIN_TOKEN="secret-token")
    r = client.post(
        "/api/v1/ml-agri/crawl-urls",
        json={
            "urls": ["https://example.test/article-1", "https://example.test/article-2"],
            "reliability_level": "internet",
            "max_pages": 2,
            "collect_links": False,
            "same_domain_only": True,
        },
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "results" in body


# ---------------------------------------------------------------------------
# 14. Admin: research-search (search engines stubbed).
# ---------------------------------------------------------------------------

def test_admin_research_search_with_stubbed_network(monkeypatch, stub_requests):
    client, _ = _boot_app(monkeypatch, NONGTRI_ADMIN_TOKEN="secret-token")
    r = client.post(
        "/api/v1/ml-agri/research-search",
        json={"query": "bệnh gỉ sắt lá cà phê", "max_results": 5, "auto_crawl": False},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "candidates" in body


def test_admin_research_batch_with_stubbed_network(monkeypatch, stub_requests):
    client, _ = _boot_app(monkeypatch, NONGTRI_ADMIN_TOKEN="secret-token")
    r = client.post(
        "/api/v1/ml-agri/research-batch",
        json={"queries": ["cà phê tái canh", "phân bón vi sinh"], "max_results": 3, "target_per_query": 2},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Endpoint shape: top-level `candidates` + grouped `groups`.
    assert "candidates" in body
    assert "groups" in body


# ---------------------------------------------------------------------------
# 15. Multi-turn chat keeps session context lightweight.
# ---------------------------------------------------------------------------

def test_chat_multiturn_history_is_respected(monkeypatch):
    client, _ = _boot_app(monkeypatch)
    session_id = f"multi-{uuid.uuid4().hex[:6]}"

    first = client.post(
        "/api/v1/ml-agri/chat",
        json={
            "question": "Cà phê vối nên bón phân thế nào?",
            "top_k": 3,
            "session_id": session_id,
            "history": [],
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/ml-agri/chat",
        json={
            "question": "Còn vào mùa khô thì sao?",
            "top_k": 3,
            "session_id": session_id,
            "history": [
                {"role": "user", "content": "Cà phê vối nên bón phân thế nào?"},
                {"role": "ai", "content": first.json()["answer"][:200]},
            ],
        },
    )
    assert second.status_code == 200
    body = second.json()
    assert body.get("session_id") == session_id


# ---------------------------------------------------------------------------
# 16. Diagnose-image quality failure path returns advice with fallback prediction.
# ---------------------------------------------------------------------------

def test_diagnose_image_quality_failure_path(monkeypatch):
    """A 320x320 black image fails brightness threshold (<45) so quality.passed=False
    and the router should still respond, with prediction.disease_label='unknown'."""
    from PIL import Image
    client, _ = _boot_app(monkeypatch)
    img = Image.new("RGB", (320, 320), (0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    payload = buf.getvalue()
    r = client.post(
        "/api/v1/ml-agri/diagnose-image",
        files={"file": ("dark.jpg", payload, "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["image_quality"]["passed"] is False
    assert body["prediction"]["disease_label"] == "unknown"
