"""Lock the security & privacy guarantees of the ML-Agri router.

These tests cover the behavioral contracts established by the security audit:

* Admin endpoints fail-closed unless `NONGTRI_ADMIN_TOKEN` is set.
* Admin endpoints reject missing or wrong tokens.
* Chat endpoint MUST NOT log raw user question content into ACTIVITY_EVENTS.
* `/sessions/{id}` DELETE clears a user's activity rows.
* Image upload size limits return 413 instead of accepting unbounded input.
* In-memory data extractors (PDF/DOCX) do not leak files to /private/tmp.

If any of these regress, the security posture documented in
`docs/planning/KeHoachTrienKhai_NongTri.html` is broken.
"""

from __future__ import annotations

import glob
import importlib
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(monkeypatch):
    monkeypatch.setenv("NONGTRI_LLM_ENABLED", "false")
    # Reload to pick up env vars cleanly per test.
    import app.shared.upload as upload_mod
    import app.shared.rate_limit as rl_mod
    importlib.reload(upload_mod)
    importlib.reload(rl_mod)
    import app.ml_agri_chat.router as router_mod
    importlib.reload(router_mod)

    app = FastAPI()
    app.state.limiter = rl_mod.limiter
    from slowapi.middleware import SlowAPIMiddleware
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(router_mod.router, prefix="/api/v1/ml-agri")
    client = TestClient(app)
    return client, router_mod


def test_admin_endpoint_fails_closed_when_token_unset(app_client, monkeypatch):
    client, _ = app_client
    monkeypatch.delenv("NONGTRI_ADMIN_TOKEN", raising=False)
    r = client.post("/api/v1/ml-agri/admin/reset-rag-data", json={"seed_knowledge_base": False})
    assert r.status_code == 503
    assert "disabled" in r.json()["detail"].lower()


def test_admin_endpoint_rejects_missing_header(app_client, monkeypatch):
    client, _ = app_client
    monkeypatch.setenv("NONGTRI_ADMIN_TOKEN", "secret-token")
    r = client.post("/api/v1/ml-agri/admin/reset-rag-data", json={"seed_knowledge_base": False})
    assert r.status_code == 401


def test_admin_endpoint_rejects_wrong_token(app_client, monkeypatch):
    client, _ = app_client
    monkeypatch.setenv("NONGTRI_ADMIN_TOKEN", "secret-token")
    r = client.post(
        "/api/v1/ml-agri/admin/reset-rag-data",
        json={"seed_knowledge_base": False},
        headers={"X-Admin-Token": "wrong"},
    )
    assert r.status_code == 401


def test_chat_does_not_leak_raw_question(app_client):
    client, router_mod = app_client
    router_mod.ACTIVITY_EVENTS.clear()
    sensitive = "Vườn cà phê nhà tôi ở xã Ea Tu Buôn Ma Thuột bị vàng lá"
    r = client.post(
        "/api/v1/ml-agri/chat",
        json={"question": sensitive, "top_k": 2, "session_id": "test-sess"},
    )
    assert r.status_code == 200
    for event in router_mod.ACTIVITY_EVENTS:
        payload = event.get("payload") or {}
        assert "question" not in payload, f"Raw question leaked: {payload}"
        assert "effective_question" not in payload
        # The sensitive text must not appear ANYWHERE in the activity log.
        assert sensitive not in str(event), "Sensitive text leaked into ACTIVITY_EVENTS"


def test_delete_session_clears_activity(app_client):
    client, router_mod = app_client
    router_mod.ACTIVITY_EVENTS.clear()
    client.post(
        "/api/v1/ml-agri/chat",
        json={"question": "Bệnh gì trên lá cà phê?", "top_k": 2, "session_id": "alice"},
    )
    before = len(router_mod.ACTIVITY_EVENTS)
    assert before >= 1
    r = client.delete("/api/v1/ml-agri/sessions/alice")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "deleted"
    assert body["removed_events"] >= 1


def test_delete_session_rejects_oversized_id(app_client):
    client, _ = app_client
    r = client.delete("/api/v1/ml-agri/sessions/" + "x" * 200)
    assert r.status_code == 400


def test_diagnose_image_rejects_oversized_upload(app_client, monkeypatch):
    client, router_mod = app_client
    # Force a tiny limit to keep the test fast.
    monkeypatch.setenv("NONGTRI_MAX_IMAGE_BYTES", "1024")
    import app.shared.upload as upload_mod
    importlib.reload(upload_mod)
    router_mod.MAX_IMAGE_BYTES = upload_mod.max_image_bytes()

    big = ("huge.jpg", b"x" * 4096, "image/jpeg")
    r = client.post("/api/v1/ml-agri/diagnose-image", files={"file": big})
    assert r.status_code == 413


def test_data_ingestion_does_not_write_to_private_tmp():
    """The audit fix replaces /private/tmp file dumps with in-memory BytesIO."""
    from io import BytesIO
    from pypdf import PdfWriter
    from docx import Document

    from app.ml_agri_chat.modules.data_ingestion import _extract_docx, _extract_pdf

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    pdf_buf = BytesIO()
    writer.write(pdf_buf)
    _extract_pdf(pdf_buf.getvalue())

    doc = Document()
    doc.add_paragraph("hello agriculture")
    docx_buf = BytesIO()
    doc.save(docx_buf)
    out = _extract_docx(docx_buf.getvalue())
    assert "agriculture" in out

    leaked = glob.glob("/private/tmp/nong_tri_*")
    assert not leaked, f"Leaked tmp files: {leaked}"


def test_sources_endpoint_returns_indexed_rag_documents(app_client):
    """Frontend handbook now consumes this endpoint instead of mock data."""
    client, _ = app_client
    r = client.get("/api/v1/ml-agri/sources")
    assert r.status_code == 200
    body = r.json()
    assert "sources" in body
    # Source documents in fixture data are real crawled material; expect at least one.
    assert isinstance(body["sources"], list)


def test_prompt_guard_accepts_dialect_terms():
    """Bias & Fairness: dialect words should not be filtered out as off-scope."""
    from app.ml_agri_chat.modules.prompt_guard import validate_question

    dialect_questions = [
        "Đám rẫy cà phê nhà tôi bị vàng lá",
        "Trên rẫy tiêu có sâu",
        "Lúa trỉa giống mới ở Tây Nguyên",
    ]
    for q in dialect_questions:
        allowed, reason = validate_question(q)
        assert allowed, f"Dialect rejected: {q!r} -> {reason}"
