"""Unit tests for the pluggable embedding store.

Covers:
- HashingEmbeddingProvider determinism + cosine sanity
- OllamaEmbeddingProvider HTTP shape + failure modes (no real network)
- Cascade fallback when Ollama is unavailable
- Auto migration on `embedding_version` mismatch at load
- reembed_all() admin path
- Search still returns top-k via boosts even when vectors come from
  different providers
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ml_agri_chat.modules import embedding_store as es


# ---------------- Hashing provider ----------------


def test_hashing_provider_is_deterministic():
    provider = es.HashingEmbeddingProvider()
    v1 = provider.embed("cà phê bị rỉ sắt lá")
    v2 = provider.embed("cà phê bị rỉ sắt lá")
    assert v1 == v2
    assert isinstance(v1, dict)
    # Normalised: sum of squares ≈ 1
    norm_sq = sum(value * value for value in v1.values())
    assert 0.99 <= norm_sq <= 1.01


def test_hashing_provider_version_is_stable():
    """Don't break existing on-disk chunks by accidentally rotating the
    version string."""
    assert es.HashingEmbeddingProvider().version == "hashing-v2-folded-keyword"


def test_hashing_cosine_sanity():
    provider = es.HashingEmbeddingProvider()
    a = provider.embed("tưới nước cà phê vào mùa khô")
    b = provider.embed("tưới nước cà phê mùa khô")
    c = provider.embed("chứng khoán cổ phiếu lên giá")
    sim_ab = es._vector_similarity(a, b)
    sim_ac = es._vector_similarity(a, c)
    assert sim_ab > sim_ac
    assert sim_ab > 0.5


# ---------------- Ollama provider ----------------


class _StubResponse:
    def __init__(self, *, status_code=200, payload=None, ok=True, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.ok = ok
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            import requests

            err = requests.HTTPError(f"HTTP {self.status_code}")
            err.response = self
            raise err


def test_ollama_provider_embed_returns_dense_list(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _StubResponse(payload={"embedding": [0.1, 0.2, 0.3, 0.4]})

    monkeypatch.setattr(es.requests, "post", fake_post)
    provider = es.OllamaEmbeddingProvider(
        model="nomic-embed-text",
        base_url="http://localhost:11434/",
        timeout_seconds=5,
    )
    vector = provider.embed("hello")
    assert vector == [0.1, 0.2, 0.3, 0.4]
    assert captured["url"] == "http://localhost:11434/api/embeddings"
    assert captured["json"]["model"] == "nomic-embed-text"
    assert captured["json"]["prompt"] == "hello"
    assert provider.version == "ollama:nomic-embed-text"


def test_ollama_provider_is_available_check(monkeypatch):
    def fake_get(url, timeout):
        return _StubResponse(payload={"models": []})

    monkeypatch.setattr(es.requests, "get", fake_get)
    provider = es.OllamaEmbeddingProvider(
        model="nomic-embed-text",
        base_url="http://localhost:11434",
        timeout_seconds=5,
    )
    assert provider.is_available() is True


def test_ollama_provider_unavailable_when_get_fails(monkeypatch):
    def fake_get(url, timeout):
        raise es.requests.ConnectionError("refused")

    monkeypatch.setattr(es.requests, "get", fake_get)
    provider = es.OllamaEmbeddingProvider(
        model="nomic-embed-text",
        base_url="http://localhost:11434",
        timeout_seconds=5,
    )
    assert provider.is_available() is False


def test_ollama_provider_raises_on_bad_response(monkeypatch):
    def fake_post(url, json, timeout):
        return _StubResponse(payload={"unexpected": "shape"})

    monkeypatch.setattr(es.requests, "post", fake_post)
    provider = es.OllamaEmbeddingProvider(
        model="nomic-embed-text",
        base_url="http://localhost:11434",
        timeout_seconds=5,
    )
    with pytest.raises(ValueError, match="missing `embedding` list"):
        provider.embed("x")


# ---------------- Cascade fallback ----------------


def test_cascade_promotes_fallback_when_primary_unavailable_at_boot(monkeypatch):
    """`_resolve_provider` should swap fallback to primary when the
    configured primary cannot be reached at start-up. This avoids burning
    a network round-trip on every embed call."""
    monkeypatch.setenv("NONGTRI_EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("NONGTRI_EMBEDDING_FALLBACK", "hashing")
    monkeypatch.setenv("NONGTRI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    def fake_get(url, timeout):
        raise es.requests.ConnectionError("daemon down")

    monkeypatch.setattr(es.requests, "get", fake_get)

    provider = es._resolve_provider()
    # When the primary is dead at boot we want the hashing provider sitting
    # at .name so the store uses its version tag.
    assert provider.name == "hashing"


def test_cascade_runtime_fallback_on_primary_error(monkeypatch):
    """If the primary succeeds is_available() but then raises during
    embed(), the cascade should still produce a vector from the fallback."""
    primary_calls = {"n": 0}

    class FlakyPrimary(es._EmbeddingProvider):
        name = "ollama"
        version = "ollama:test"

        def is_available(self):
            return True

        def embed(self, text):
            primary_calls["n"] += 1
            raise RuntimeError("rate limited")

    cascade = es._CascadeEmbeddingProvider(
        FlakyPrimary(), es.HashingEmbeddingProvider()
    )
    vector = cascade.embed("xin chào")
    assert isinstance(vector, dict)  # fell back to hashing's sparse dict
    assert primary_calls["n"] == 1


def test_cascade_runtime_no_fallback_raises(monkeypatch):
    class AlwaysFail(es._EmbeddingProvider):
        name = "ollama"
        version = "ollama:test"

        def is_available(self):
            return True

        def embed(self, text):
            raise RuntimeError("boom")

    cascade = es._CascadeEmbeddingProvider(AlwaysFail(), None)
    with pytest.raises(RuntimeError, match="boom"):
        cascade.embed("x")


# ---------------- Vector similarity helper ----------------


def test_vector_similarity_dense_and_sparse_paths():
    # Dense
    assert es._vector_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert es._vector_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    # Sparse
    a = {"5": 0.7, "9": 0.7}
    b = {"5": 0.7, "9": 0.7}
    assert es._vector_similarity(a, b) > 0.9
    # Empty
    assert es._vector_similarity([], [1, 2]) == 0.0
    assert es._vector_similarity({}, {"a": 1.0}) == 0.0
    # Length mismatch (dense) -> 0
    assert es._vector_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0
    # Mixed shape -> 0 (cannot compare across spaces)
    assert es._vector_similarity([1.0, 0.0], {"0": 1.0}) == 0.0


# ---------------- EmbeddingStore (with hashing) ----------------


def _make_chunk(chunk_id: str, text: str, source_id: str = "src1", title: str = "Doc") -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": {
            "source_id": source_id,
            "title": title,
            "url": None,
            "reliability_level": "manual",
        },
    }


def test_store_add_chunks_persists_with_active_version(tmp_path: Path):
    store = es.EmbeddingStore(tmp_path, provider=es.HashingEmbeddingProvider())
    added = store.add_chunks(
        [
            _make_chunk("c1", "trồng cà phê arabica vùng Tây Nguyên"),
            _make_chunk("c2", "cây cà phê bị rỉ sắt lá nâu cam"),
        ]
    )
    assert added == 2
    on_disk = json.loads((tmp_path / "chunks.json").read_text(encoding="utf-8"))
    assert all(item["embedding_version"] == es.HashingEmbeddingProvider().version for item in on_disk)


def test_store_auto_migration_on_version_mismatch(tmp_path: Path):
    """A store written by a different embedding version should re-embed
    on load with the active provider's version."""
    legacy_chunks = [
        {
            "chunk_id": "c1",
            "text": "tưới cà phê",
            "embedding": {"99": 1.0},  # legacy sparse vector
            "embedding_version": "legacy-version-xyz",
            "metadata": {"source_id": "s1", "title": "Doc"},
        }
    ]
    (tmp_path / "chunks.json").write_text(
        json.dumps(legacy_chunks, ensure_ascii=False), encoding="utf-8"
    )

    store = es.EmbeddingStore(tmp_path, provider=es.HashingEmbeddingProvider())
    on_disk = json.loads((tmp_path / "chunks.json").read_text(encoding="utf-8"))
    assert on_disk[0]["embedding_version"] == es.HashingEmbeddingProvider().version
    # The legacy vector must have been replaced.
    assert on_disk[0]["embedding"] != {"99": 1.0}


def test_store_reembed_all_updates_every_chunk(tmp_path: Path):
    """The admin endpoint calls this to force a clean reindex."""

    class TrackingProvider(es.HashingEmbeddingProvider):
        version = "tracking-v1"

        def __init__(self):
            super().__init__()
            self.calls = 0

        def embed(self, text):
            self.calls += 1
            return super().embed(text)

    initial = TrackingProvider()
    store = es.EmbeddingStore(tmp_path, provider=initial)
    store.add_chunks(
        [_make_chunk(f"c{i}", f"text {i} cà phê") for i in range(5)]
    )
    # New provider with a different version (simulating a swap).
    new = TrackingProvider()
    new.version = "tracking-v2"
    store._provider = new

    updated = store.reembed_all()
    assert updated == 5
    on_disk = json.loads((tmp_path / "chunks.json").read_text(encoding="utf-8"))
    assert all(item["embedding_version"] == "tracking-v2" for item in on_disk)


def test_store_search_returns_top_k_by_score(tmp_path: Path):
    """Smoke test the full path: add chunks, search, expect the most
    keyword-aligned result on top. Verifies hashing + boosts still work."""
    store = es.EmbeddingStore(tmp_path, provider=es.HashingEmbeddingProvider())
    store.add_chunks(
        [
            _make_chunk(
                "c-rust",
                "cây cà phê bị rỉ sắt lá nâu cam triệu chứng quan sát rõ trên mặt dưới lá",
                source_id="rust",
                title="Bệnh rỉ sắt cà phê",
            ),
            _make_chunk(
                "c-harvest",
                "thời điểm thu hoạch cà phê arabica vào tháng 11",
                source_id="harvest",
                title="Thu hoạch cà phê",
            ),
            _make_chunk(
                "c-unrelated",
                "cách nấu phở bò chuẩn vị Hà Nội",
                source_id="pho",
                title="Phở",
            ),
        ]
    )
    results = store.search("triệu chứng rỉ sắt lá cà phê", top_k=2)
    assert results, "Expected non-empty search results"
    assert results[0]["metadata"]["source_id"] == "rust"
    assert all(r["metadata"]["source_id"] != "pho" for r in results)


def test_store_dedupes_repeated_chunks_on_load(tmp_path: Path):
    """Defensive: legacy stores accidentally containing duplicates should
    be deduped on load (one of the very old bugs)."""
    duplicates = [
        {
            "chunk_id": "c1",
            "text": "tưới cà phê",
            "embedding": {"1": 1.0},
            "embedding_version": es.HashingEmbeddingProvider().version,
            "metadata": {"source_id": "s1", "title": "Doc"},
        },
        {
            "chunk_id": "c2",
            "text": "tưới cà phê",  # exact same text + source -> dupe
            "embedding": {"1": 1.0},
            "embedding_version": es.HashingEmbeddingProvider().version,
            "metadata": {"source_id": "s1", "title": "Doc"},
        },
    ]
    (tmp_path / "chunks.json").write_text(
        json.dumps(duplicates, ensure_ascii=False), encoding="utf-8"
    )
    store = es.EmbeddingStore(tmp_path, provider=es.HashingEmbeddingProvider())
    on_disk = json.loads((tmp_path / "chunks.json").read_text(encoding="utf-8"))
    assert len(on_disk) == 1
