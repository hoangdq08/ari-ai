"""KPI proxies for slide 13 of the AI presentation.

Locks in the Recall@k / MRR / cite-rate / refusal-rate from
`/api/v1/ml-agri/rag-evaluate` and the latency p50/p95 from
`/api/v1/ml-agri/admin/ops-events`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(monkeypatch):
    monkeypatch.setenv("NONGTRI_LLM_ENABLED", "false")
    monkeypatch.setenv("NONGTRI_RATE_LIMIT_CHAT", "1000/minute")
    monkeypatch.setenv("NONGTRI_RATE_LIMIT_IMAGE", "1000/minute")
    monkeypatch.setenv("NONGTRI_RATE_LIMIT_ADMIN", "1000/minute")
    monkeypatch.setenv("NONGTRI_ADMIN_TOKEN", "secret-token")

    import app.shared.upload as upload_mod
    import app.shared.rate_limit as rl_mod
    import app.shared.latency as latency_mod
    importlib.reload(upload_mod)
    importlib.reload(rl_mod)
    importlib.reload(latency_mod)

    import app.main as main_mod
    importlib.reload(main_mod)

    app = main_mod.get_application()
    return TestClient(app)


def test_rag_evaluate_reports_recall_mrr_cite_rate(app_client):
    """Slide 13 KPI numbers must be present in the response payload."""
    r = app_client.post("/api/v1/ml-agri/rag-evaluate", json={"top_k": 5})
    assert r.status_code == 200, r.text
    body = r.json()
    summary = body["summary"]

    # Numeric KPIs must exist and live in [0, 1].
    for key in ("recall_at_k", "mrr", "cite_rate", "refusal_rate", "pass_rate"):
        assert key in summary, f"missing KPI: {key}"
        assert isinstance(summary[key], (int, float)), key
        assert 0.0 <= summary[key] <= 1.0, f"{key} out of [0,1]: {summary[key]}"

    # Refusal + cite should partition the case set (one of the two per case).
    assert round(summary["cite_rate"] + summary["refusal_rate"], 3) == 1.0
    assert summary["top_k"] == 5

    # Per-case rows should include per-case recall and reciprocal rank.
    for case in body["results"]:
        assert "recall_at_k" in case
        assert "reciprocal_rank" in case


def test_admin_ops_events_exposes_latency_report(app_client):
    """Slide 13 latency p50 must be a real measured number."""
    # Generate some traffic so the latency buffer has samples.
    for _ in range(5):
        app_client.get("/api/v1/ml-agri/health")
    app_client.post(
        "/api/v1/ml-agri/chat",
        json={"question": "Cách tưới nước cà phê mùa khô?", "top_k": 2, "session_id": "kpi"},
    )

    r = app_client.get(
        "/api/v1/ml-agri/admin/ops-events",
        headers={"X-Admin-Token": "secret-token"},
    )
    assert r.status_code == 200
    body = r.json()

    assert "latency" in body
    latency = body["latency"]
    assert latency["samples"] >= 5
    assert latency["p50_ms"] > 0
    assert latency["p95_ms"] >= latency["p50_ms"]
    assert isinstance(latency["by_route"], list)
    # At least one route entry exists with a sensible payload.
    sample = latency["by_route"][0]
    for key in ("route", "count", "p50_ms", "p95_ms", "max_ms"):
        assert key in sample


def test_response_header_carries_process_time(app_client):
    """Latency middleware should attach `X-Process-Time-Ms` for client debugging."""
    r = app_client.get("/api/v1/ml-agri/health")
    assert r.status_code == 200
    assert "x-process-time-ms" in {h.lower() for h in r.headers.keys()}
    value = float(r.headers["x-process-time-ms"])
    assert value >= 0.0
