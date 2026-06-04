from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

from .source_policy import infer_reliability, source_penalty


TOKEN_RE = re.compile(r"\w+", re.UNICODE)
EMBEDDING_VERSION = "hashing-v2-folded-keyword"
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


class EmbeddingStore:
    """ChromaDB-shaped interface with deterministic JSON fallback."""

    def __init__(self, store_dir: str | Path):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = self.store_dir / "chunks.json"
        self._chunks = self._load()

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
            item["embedding"] = _embed(item["text"])
            item["embedding_version"] = EMBEDDING_VERSION
            self._chunks.append(item)
            added += 1
        self._persist()
        return added

    def rebuild(self, chunks: list[dict[str, Any]]) -> int:
        self._chunks = []
        return self.add_chunks(chunks)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_embedding = _embed(query)
        query_tokens = _tokens(query)
        query_phrases = _query_phrases(query_tokens)
        results = []
        for chunk in self._chunks:
            chunk_text = _fold_vietnamese(chunk.get("text", "").lower())
            metadata = chunk.get("metadata", {})
            title_text = _fold_vietnamese(str(metadata.get("title") or "").lower())
            reliability_level = infer_reliability(metadata.get("url"), metadata.get("reliability_level", "internet"))
            penalty = source_penalty(metadata.get("title"), metadata.get("url"), chunk.get("text", ""))
            score = (
                _cosine(query_embedding, chunk.get("embedding", {}))
                + _keyword_boost(query_tokens, query_phrases, chunk_text)
                + _title_boost(query_tokens, query_phrases, title_text)
                + _domain_phrase_boost(query_tokens, f"{title_text} {chunk_text}")
                + RELIABILITY_BOOST.get(reliability_level, 0.0)
                - penalty
            )
            if score > 0.02:
                payload = {k: v for k, v in chunk.items() if k != "embedding"}
                payload.setdefault("metadata", {})
                payload["metadata"]["reliability_level"] = reliability_level
                payload["score"] = round(score, 4)
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
        for chunk in chunks:
            if chunk.get("embedding_version") != EMBEDDING_VERSION:
                chunk["embedding"] = _embed(chunk.get("text", ""))
                chunk["embedding_version"] = EMBEDDING_VERSION
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


def _embed(text: str, dims: int = 256) -> dict[str, float]:
    vector: dict[str, float] = {}
    for token in _tokens(text):
        bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % dims
        key = str(bucket)
        vector[key] = vector.get(key, 0.0) + 1.0
    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {key: value / norm for key, value in vector.items()}


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


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
