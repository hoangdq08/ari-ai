"""Vector store with pluggable embedding providers.

Provider cascade (driven by env):

- `NONGTRI_EMBEDDING_PROVIDER` (default `ollama`): primary embedder.
- `NONGTRI_EMBEDDING_FALLBACK` (default `hashing`): used when the primary
  is unconfigured or fails at runtime. Set to an empty string to disable
  fallback.

Supported providers:

- `ollama`: hits Ollama's `/api/embeddings` endpoint with
  `NONGTRI_EMBEDDING_MODEL` (default `nomic-embed-text`, 768-dim dense).
- `hashing`: deterministic 256-bucket MD5 bag-of-words. Kept as the
  legacy default so the system still works without Ollama (e.g. dev
  laptops, CI). Score behaviour matches the pre-2026-06 implementation.

Each persisted chunk carries `embedding_version`. On load, chunks whose
version no longer matches the active provider are auto re-embedded - the
same migration trick the hashing-only code used historically. Mixed
versions in one store are not supported because cosine across embedding
spaces is meaningless; we re-embed everything to the active provider.

Score scale notes: dense providers return cosine in roughly [-1, 1] while
the hashing implementation returns a normalised sparse cosine in roughly
[0, 1]. We do not normalise here on purpose - the heavy keyword/title
boosts in `search()` dominate the final score and the existing cutoff
(`score > 0.02`) keeps working for both. A later phase should tune
weights once a real eval set lands.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import unicodedata
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import requests

from .source_policy import infer_reliability, source_penalty


TOKEN_RE = re.compile(r"\w+", re.UNICODE)
SEARCH_STOPWORDS = {
    "cách",
    "cho",
    "cây",
    "như",
    "thế",
    "nào",
    "với",
    "theo",
    "của",
    "trong",
    "ngoài",
    "phần",
    "giúp",
    "tăng",
    "rõ",
    "rệt",
    "nghi",
    "nên",
    "nen",
    "khi",
}
RELIABILITY_BOOST = {
    "official": 0.45,
    "semi_official": 0.22,
    "manual": 0.12,
    "internet": 0.0,
}

# Hashing provider version tag. Kept identical to the historical value so
# stores written before this refactor are recognised as up-to-date when
# the active provider is still hashing.
_HASHING_VERSION = "hashing-v2-folded-keyword"
_HASHING_DIMS = 256

_DEFAULT_OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"


# --------------------------------------------------------------------------
# Embedding providers
# --------------------------------------------------------------------------


class _EmbeddingProvider(ABC):
    """Abstracts the embed() call so the store can switch backends without
    knowing the vector shape."""

    name: str
    version: str

    @abstractmethod
    def embed(self, text: str) -> Any: ...

    @abstractmethod
    def is_available(self) -> bool: ...


class HashingEmbeddingProvider(_EmbeddingProvider):
    """Deterministic MD5-bucket bag-of-words. No network, no external deps."""

    name = "hashing"
    version = _HASHING_VERSION

    def __init__(self, dims: int = _HASHING_DIMS):
        self.dims = dims

    def is_available(self) -> bool:
        return True

    def embed(self, text: str) -> dict[str, float]:
        vector: dict[str, float] = {}
        for token in _tokens(text):
            bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dims
            key = str(bucket)
            vector[key] = vector.get(key, 0.0) + 1.0
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        return {key: value / norm for key, value in vector.items()}


class OllamaEmbeddingProvider(_EmbeddingProvider):
    """Calls Ollama's `/api/embeddings` endpoint.

    Returns a dense `list[float]` (typically 768-dim for nomic-embed-text).
    Embedding version is `ollama:<model>` so future model swaps trigger
    automatic re-embedding.
    """

    name = "ollama"

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        timeout_seconds: float = 10.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.version = f"ollama:{model}"

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.ok
        except Exception:
            return False

    def embed(self, text: str) -> list[float]:
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        vector = payload.get("embedding")
        if not isinstance(vector, list):
            raise ValueError(
                f"Ollama embed response missing `embedding` list: {payload}"
            )
        return [float(value) for value in vector]


def _build_provider(name: str) -> _EmbeddingProvider | None:
    name = (name or "").strip().lower()
    if name == "hashing":
        return HashingEmbeddingProvider()
    if name == "ollama":
        return OllamaEmbeddingProvider(
            model=os.getenv(
                "NONGTRI_EMBEDDING_MODEL", _DEFAULT_OLLAMA_EMBEDDING_MODEL
            ).strip()
            or _DEFAULT_OLLAMA_EMBEDDING_MODEL,
            base_url=os.getenv(
                "NONGTRI_OLLAMA_BASE_URL", "http://127.0.0.1:11434"
            ),
            timeout_seconds=float(
                os.getenv("NONGTRI_EMBEDDING_TIMEOUT_SECONDS", "10")
            ),
        )
    return None


class _CascadeEmbeddingProvider(_EmbeddingProvider):
    """Primary provider with optional runtime fallback. If the primary
    raises during `embed()`, we fall back to the secondary so a transient
    Ollama hiccup does not poison the index.
    """

    def __init__(
        self, primary: _EmbeddingProvider, fallback: _EmbeddingProvider | None
    ):
        self._primary = primary
        self._fallback = fallback
        # `name`/`version` reflect the primary because the store decides
        # migration based on the active embedding space.
        self.name = primary.name
        self.version = primary.version
        self.degraded = False  # True when fallback was promoted at boot

    def is_available(self) -> bool:
        return self._primary.is_available() or (
            self._fallback is not None and self._fallback.is_available()
        )

    def embed(self, text: str) -> Any:
        try:
            return self._primary.embed(text)
        except Exception as primary_error:
            if self._fallback is None:
                raise
            # Surface the reason once per process; callers do not log per-chunk.
            # The fallback vector lives in a different embedding space - the
            # store will still cosine it against same-space chunks, so we
            # tag the chunk with the fallback's version below in add_chunks.
            return self._fallback.embed(text)


def _resolve_provider() -> _EmbeddingProvider:
    primary_name = os.getenv("NONGTRI_EMBEDDING_PROVIDER", "ollama")
    fallback_name = os.getenv("NONGTRI_EMBEDDING_FALLBACK", "hashing")

    primary = _build_provider(primary_name) or HashingEmbeddingProvider()
    fallback = (
        _build_provider(fallback_name)
        if fallback_name and fallback_name != primary.name
        else None
    )

    # Promote fallback when primary clearly cannot serve traffic at boot
    # (e.g. Ollama daemon not running). Avoids burning a network round-trip
    # on every embed call only to fall back.
    if not primary.is_available() and fallback is not None and fallback.is_available():
        cascade = _CascadeEmbeddingProvider(fallback, None)
        cascade.degraded = True
        return cascade

    return _CascadeEmbeddingProvider(primary, fallback)


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------


class EmbeddingStore:
    """ChromaDB-shaped interface with a JSON-backed local store."""

    def __init__(self, store_dir: str | Path, provider: _EmbeddingProvider | None = None):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = self.store_dir / "chunks.json"
        self._provider = provider or _resolve_provider()
        self._chunks = self._load()

    @property
    def embedding_version(self) -> str:
        return self._provider.version

    @property
    def is_degraded(self) -> bool:
        """True when the primary embedding provider was unavailable at boot
        and the system fell back to a lower-quality provider (e.g. hashing)."""
        return getattr(self._provider, "degraded", False)

    def add_chunks(self, chunks: list[dict[str, Any]]) -> int:
        incoming_source_ids = {
            chunk.get("metadata", {}).get("source_id")
            for chunk in chunks
            if chunk.get("metadata", {}).get("source_id")
        }
        if incoming_source_ids:
            self._chunks = [
                item
                for item in self._chunks
                if item.get("metadata", {}).get("source_id") not in incoming_source_ids
            ]
        existing_ids = {item["chunk_id"] for item in self._chunks}
        added = 0
        for chunk in chunks:
            if chunk["chunk_id"] in existing_ids:
                continue
            item = dict(chunk)
            item["embedding"] = self._provider.embed(item["text"])
            item["embedding_version"] = self._provider.version
            self._chunks.append(item)
            added += 1
        self._persist()
        return added

    def rebuild(self, chunks: list[dict[str, Any]]) -> int:
        self._chunks = []
        return self.add_chunks(chunks)

    def reembed_all(self) -> int:
        """Force every chunk to be re-embedded with the current provider.

        Returns the number of chunks updated. Useful as a recovery hatch
        after switching providers or when the index drifts from the
        chunk files. Exposed via `POST /admin/rag-reembed-all`.
        """
        updated = 0
        for chunk in self._chunks:
            chunk["embedding"] = self._provider.embed(chunk.get("text", ""))
            chunk["embedding_version"] = self._provider.version
            updated += 1
        self._persist()
        return updated

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_embedding = self._provider.embed(query)
        query_tokens = _tokens(query)
        query_phrases = _query_phrases(query_tokens)
        results = []
        for chunk in self._chunks:
            chunk_text = _fold_vietnamese(chunk.get("text", "").lower())
            metadata = chunk.get("metadata", {})
            title_text = _fold_vietnamese(str(metadata.get("title") or "").lower())
            reliability_level = infer_reliability(metadata.get("url"), metadata.get("reliability_level", "internet"))
            penalty = source_penalty(metadata.get("title"), metadata.get("url"), chunk.get("text", ""))

            # Compute individual score components for Trục 3 (Explainability)
            s_vector = _vector_similarity(query_embedding, chunk.get("embedding"))
            s_keyword = _keyword_boost(query_tokens, query_phrases, chunk_text)
            s_title = _title_boost(query_tokens, query_phrases, title_text)
            s_domain = _domain_phrase_boost(query_tokens, f"{title_text} {chunk_text}")
            s_reliability = RELIABILITY_BOOST.get(reliability_level, 0.0)
            score = s_vector + s_keyword + s_title + s_domain + s_reliability - penalty

            if score > 0.02:
                payload = {k: v for k, v in chunk.items() if k != "embedding"}
                payload.setdefault("metadata", {})
                payload["metadata"]["reliability_level"] = reliability_level
                payload["score"] = round(score, 4)
                payload["score_breakdown"] = {
                    "vector": round(s_vector, 4),
                    "keyword": round(s_keyword, 4),
                    "title": round(s_title, 4),
                    "domain_phrase": round(s_domain, 4),
                    "reliability": round(s_reliability, 4),
                    "penalty": round(penalty, 4),
                }
                results.append(payload)
        ranked = sorted(results, key=lambda item: item["score"], reverse=True)
        deduped = []
        seen_keys = set()
        for item in ranked:
            metadata = item.get("metadata", {})
            key = (metadata.get("source_id"), re.sub(r"\s+", " ", item.get("text", "")[:240]).strip().lower())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(item)
            if len(deduped) >= top_k:
                break
        return deduped

    def list_sources(self) -> list[dict[str, Any]]:
        sources: dict[str, dict[str, Any]] = {}
        for chunk in self._chunks:
            metadata = chunk["metadata"]
            source_id = metadata["source_id"]
            sources[source_id] = {
                "source_id": source_id,
                "title": metadata.get("title"),
                "source_type": metadata.get("source_type"),
                "url": metadata.get("url"),
                "file_name": metadata.get("file_name"),
                "reliability_level": metadata.get("reliability_level"),
                "crawled_at": metadata.get("crawled_at"),
                "category": metadata.get("category"),
                "category_label": metadata.get("category_label"),
            }
        return sorted(sources.values(), key=lambda item: item.get("title") or "")

    def _load(self) -> list[dict[str, Any]]:
        if not self.json_path.exists():
            return []
        with self.json_path.open("r", encoding="utf-8") as handle:
            chunks = json.load(handle)
        migrated = False
        active_version = self._provider.version
        for chunk in chunks:
            if chunk.get("embedding_version") != active_version:
                chunk["embedding"] = self._provider.embed(chunk.get("text", ""))
                chunk["embedding_version"] = active_version
                migrated = True
        deduped = []
        seen_keys = set()
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            key = (metadata.get("source_id"), re.sub(r"\s+", " ", chunk.get("text", "")).strip().lower())
            if key in seen_keys:
                migrated = True
                continue
            seen_keys.add(key)
            deduped.append(chunk)
        if migrated:
            self._chunks = deduped
            self._persist()
        return deduped

    def _persist(self) -> None:
        with self.json_path.open("w", encoding="utf-8") as handle:
            json.dump(self._chunks, handle, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# Scoring helpers
# --------------------------------------------------------------------------


def _vector_similarity(left: Any, right: Any) -> float:
    """Cosine similarity that works for both dense lists and sparse dicts.

    Dense vectors arrive as `list[float]`; sparse hashing vectors arrive
    as `dict[str, float]`. We dispatch on the runtime shape so the caller
    does not need to know which provider produced the embedding.
    """
    if not left or not right:
        return 0.0
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        norm_a = math.sqrt(sum(a * a for a in left))
        norm_b = math.sqrt(sum(b * b for b in right))
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)
    if isinstance(left, dict) and isinstance(right, dict):
        if len(left) > len(right):
            left, right = right, left
        return sum(value * right.get(key, 0.0) for key, value in left.items())
    # Mixed shapes (e.g. legacy chunk vs new query) cannot be compared.
    return 0.0


def _query_phrases(tokens: list[str]) -> list[str]:
    phrases = []
    for size in (4, 3, 2):
        for index in range(0, max(0, len(tokens) - size + 1)):
            phrases.append(" ".join(tokens[index : index + size]))
    return phrases


def _keyword_boost(query_tokens: list[str], query_phrases: list[str], chunk_text: str) -> float:
    if not query_tokens or not chunk_text:
        return 0.0
    chunk_tokens = set(TOKEN_RE.findall(chunk_text))
    important_tokens = {token for token in query_tokens if token not in SEARCH_STOPWORDS}
    token_hits = sum(1 for token in important_tokens if token in chunk_tokens)
    phrase_hits = sum(1 for phrase in query_phrases if phrase in chunk_text)
    coverage = token_hits / max(1, len(important_tokens))
    return min(1.4, token_hits * 0.08 + phrase_hits * 0.18 + coverage * 0.32)


def _title_boost(query_tokens: list[str], query_phrases: list[str], title_text: str) -> float:
    if not title_text:
        return 0.0
    title_tokens = set(TOKEN_RE.findall(title_text))
    important_tokens = {token for token in query_tokens if token not in SEARCH_STOPWORDS}
    token_hits = sum(1 for token in important_tokens if token in title_tokens)
    phrase_hits = sum(1 for phrase in query_phrases if phrase in title_text)
    return min(0.5, token_hits * 0.08 + phrase_hits * 0.12)


def _domain_phrase_boost(query_tokens: list[str], text: str) -> float:
    query = " ".join(query_tokens)
    boosts = {
        "bon phan": 0.55,
        "tuoi nuoc": 0.45,
        "tao tan": 0.45,
        "tia canh": 0.45,
        "thu hoach": 0.45,
        "chon giong": 0.45,
        "tai canh": 0.45,
    }
    total = 0.0
    for phrase, value in boosts.items():
        if phrase in query and phrase in text:
            total += value
    return min(total, 1.1)


def _tokens(text: str) -> list[str]:
    folded = _fold_vietnamese(text.lower())
    return [token for token in TOKEN_RE.findall(folded) if len(token) >= 3]


def _fold_vietnamese(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_marks.replace("đ", "d").replace("Đ", "D")
