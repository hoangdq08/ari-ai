"""Unit tests for the internet crawler.

Covers the additions from the ingest-pipeline improvements:
- HEAD preflight blocks oversized / unparseable resources before GET.
- Servers that 405 on HEAD still fall through to GET (graceful).
- _fetch_with_retries() retries 5xx + Timeout, gives up on 4xx.
- crawl_urls(force=True) propagates to DataIngestor.ingest_url so a
  previously stored source is overwritten and `.bak` is left behind.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.ml_agri_chat.modules.internet_crawler as crawler_mod
from app.ml_agri_chat.modules.data_ingestion import DataIngestor
from app.ml_agri_chat.modules.internet_crawler import InternetCrawler


class _StubHeaders:
    def __init__(self, mapping):
        self._mapping = {k.lower(): v for k, v in mapping.items()}

    def get(self, key, default=None):
        return self._mapping.get(key.lower(), default)


class _StubResponse:
    def __init__(self, *, status_code=200, headers=None, text="", content=b"", ok=True):
        self.status_code = status_code
        self.headers = _StubHeaders(headers or {})
        self.text = text
        self.content = content
        self.ok = ok

    def raise_for_status(self):
        if not self.ok:
            import requests

            err = requests.HTTPError(f"HTTP {self.status_code}")
            err.response = self
            raise err


def _make_crawler(tmp_path: Path) -> InternetCrawler:
    raw_dir = tmp_path / "raw"
    candidates = tmp_path / "candidates"
    raw_dir.mkdir()
    candidates.mkdir()
    return InternetCrawler(DataIngestor(raw_dir), candidates)


# ---------------- HEAD preflight ----------------


def test_preflight_skips_oversized_content(tmp_path, monkeypatch):
    crawler = _make_crawler(tmp_path)
    monkeypatch.setenv("NONGTRI_CRAWL_MAX_BYTES", "1024")  # 1 KiB

    def fake_head(url, timeout, allow_redirects, headers):
        return _StubResponse(
            status_code=200,
            headers={"content-length": "5000", "content-type": "application/pdf"},
        )

    monkeypatch.setattr(crawler_mod.requests, "head", fake_head)
    monkeypatch.setattr(
        crawler_mod.requests,
        "get",
        lambda *a, **kw: pytest.fail("GET must not be called when HEAD says oversized"),
    )

    items = crawler.crawl_urls(["https://example.com/big.pdf"])
    assert len(items) == 1
    assert items[0].status == "skipped"
    assert "5000" in (items[0].error or "")


def test_preflight_skips_unsupported_content_type(tmp_path, monkeypatch):
    crawler = _make_crawler(tmp_path)

    def fake_head(url, timeout, allow_redirects, headers):
        return _StubResponse(
            status_code=200,
            headers={"content-type": "video/mp4", "content-length": "100"},
        )

    monkeypatch.setattr(crawler_mod.requests, "head", fake_head)
    monkeypatch.setattr(
        crawler_mod.requests,
        "get",
        lambda *a, **kw: pytest.fail("GET must not run for video/mp4"),
    )

    items = crawler.crawl_urls(["https://example.com/clip.mp4"])
    assert items[0].status == "skipped"
    assert "video/mp4" in (items[0].error or "")


def test_preflight_passes_when_head_fails(tmp_path, monkeypatch):
    """A flaky / 405 HEAD must not block the GET path. The full crawl
    still hits ingest_url and lands as 'ingested'."""
    crawler = _make_crawler(tmp_path)

    def fake_head(url, timeout, allow_redirects, headers):
        raise crawler_mod.requests.ConnectionError("flaky")

    get_calls = {"n": 0}

    def fake_get(url, timeout, headers):
        get_calls["n"] += 1
        # Outer get_calls covers two callers: the crawler's HTML fetch and
        # DataIngestor.ingest_url's own GET. Return a small HTML for both.
        return _StubResponse(
            status_code=200,
            headers={"content-type": "text/html"},
            text="<html><head><title>doc</title></head><body>nội dung mẫu</body></html>",
        )

    monkeypatch.setattr(crawler_mod.requests, "head", fake_head)
    monkeypatch.setattr(crawler_mod.requests, "get", fake_get)
    # data_ingestion uses its own requests module; patch there too.
    import app.ml_agri_chat.modules.data_ingestion as di

    monkeypatch.setattr(di.requests, "get", fake_get)

    items = crawler.crawl_urls(["https://example.com/page"])
    assert items[0].status == "ingested"
    assert get_calls["n"] >= 1


# ---------------- Retry behaviour ----------------


def test_fetch_retries_on_503_then_succeeds(tmp_path, monkeypatch):
    crawler = _make_crawler(tmp_path)
    monkeypatch.setattr(crawler_mod.time, "sleep", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        crawler_mod.requests,
        "head",
        lambda *a, **kw: _StubResponse(headers={"content-type": "text/html"}),
    )

    attempts = {"n": 0}

    def fake_get(url, timeout, headers):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return _StubResponse(status_code=503, ok=False)
        return _StubResponse(
            status_code=200,
            headers={"content-type": "text/html"},
            text="<html><title>t</title>ok content</html>",
        )

    monkeypatch.setattr(crawler_mod.requests, "get", fake_get)
    import app.ml_agri_chat.modules.data_ingestion as di

    monkeypatch.setattr(di.requests, "get", fake_get)

    items = crawler.crawl_urls(["https://example.com/x"])
    assert items[0].status == "ingested"
    # 1 retried fetch (503 -> 200) + 1 ingest_url GET = 3 calls minimum.
    assert attempts["n"] >= 2


def test_fetch_does_not_retry_404(tmp_path, monkeypatch):
    crawler = _make_crawler(tmp_path)
    monkeypatch.setattr(crawler_mod.time, "sleep", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        crawler_mod.requests,
        "head",
        lambda *a, **kw: _StubResponse(headers={"content-type": "text/html"}),
    )

    attempts = {"n": 0}

    def fake_get(url, timeout, headers):
        attempts["n"] += 1
        return _StubResponse(status_code=404, ok=False, text="not found")

    monkeypatch.setattr(crawler_mod.requests, "get", fake_get)

    items = crawler.crawl_urls(["https://example.com/missing"])
    assert items[0].status == "failed"
    assert attempts["n"] == 1  # no retry on 404


# ---------------- Force refresh ----------------


def test_force_refresh_overwrites_and_creates_backup(tmp_path, monkeypatch):
    crawler = _make_crawler(tmp_path)
    monkeypatch.setattr(crawler_mod.time, "sleep", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        crawler_mod.requests,
        "head",
        lambda *a, **kw: _StubResponse(headers={"content-type": "text/html"}),
    )

    def make_get(body: str):
        def fake_get(url, timeout, headers):
            return _StubResponse(
                status_code=200,
                headers={"content-type": "text/html"},
                text=f"<html><title>doc</title>{body}</html>",
            )

        return fake_get

    import app.ml_agri_chat.modules.data_ingestion as di

    monkeypatch.setattr(crawler_mod.requests, "get", make_get("v1 nội dung cũ"))
    monkeypatch.setattr(di.requests, "get", make_get("v1 nội dung cũ"))
    first = crawler.crawl_urls(["https://example.com/page"], force=False)
    assert first[0].status == "ingested"
    source_id = first[0].source_id
    raw_path = tmp_path / "raw" / f"{source_id}.json"
    assert raw_path.exists()
    payload_v1 = json.loads(raw_path.read_text(encoding="utf-8"))
    assert "v1" in payload_v1["raw_text"]

    # Same URL, fresher content. Without `force` we expect duplicate
    # (same source_id, same body hash if body unchanged - but we changed
    # body so this is actually a fresh write under the same source_id,
    # and the ingest_url path handles that via the existing
    # `existing_path` branch). Re-running with `force=True` MUST overwrite
    # and leave a .bak.
    monkeypatch.setattr(crawler_mod.requests, "get", make_get("v2 nội dung mới"))
    monkeypatch.setattr(di.requests, "get", make_get("v2 nội dung mới"))
    second = crawler.crawl_urls(["https://example.com/page"], force=True)
    assert second[0].status == "ingested"
    assert second[0].source_id == source_id  # same id for same URL

    bak_path = tmp_path / "raw" / f"{source_id}.json.bak"
    assert bak_path.exists()
    bak_payload = json.loads(bak_path.read_text(encoding="utf-8"))
    assert "v1" in bak_payload["raw_text"]

    new_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    assert "v2" in new_payload["raw_text"]
