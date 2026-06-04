from __future__ import annotations

from pathlib import Path
from typing import Any

from .embedding_store import EmbeddingStore
from .taxonomy import category_matches, classify_query

SEED_SOURCE_IDS = {
    "than_thu",
    "gi_sat_la_ca_phe",
    "dom_mat_cua",
    "cay_khoe",
    "coffee_leaf_rust",
    "cercospora_leaf_spot",
    "anthracnose",
    "healthy",
}


class AgriculturalRAG:
    def __init__(self, vector_store_dir: str | Path):
        self.store = EmbeddingStore(vector_store_dir)

    def add_chunks(self, chunks: list[dict[str, Any]]) -> int:
        return self.store.add_chunks(chunks)

    def rebuild(self, chunks: list[dict[str, Any]]) -> int:
        return self.store.rebuild(chunks)

    def retrieve(self, query: str, top_k: int = 5, category_key: str | None = None) -> list[dict[str, Any]]:
        target_category = category_key or classify_query(query)["category"]
        candidates = [
            chunk
            for chunk in self.store.search(query, top_k=max(top_k * 8, 40))
            if not _is_seed_sample(chunk)
        ]
        scoped = [chunk for chunk in candidates if category_matches(chunk, target_category)]
        return scoped[:top_k]

    def sources(self) -> list[dict[str, Any]]:
        return self.store.list_sources()

    def retrieve_for_label(self, disease_label: str, observed_symptoms: list[str], top_k: int = 4) -> list[dict[str, Any]]:
        query = f"{disease_label} {' '.join(observed_symptoms)} cà phê triệu chứng nguyên nhân xử lý"
        return self.retrieve(query, top_k=top_k)


def _is_seed_sample(chunk: dict[str, Any]) -> bool:
    metadata = chunk.get("metadata", {})
    source_id = metadata.get("source_id")
    file_name = metadata.get("file_name")
    return bool(metadata.get("seed_sample") or source_id in SEED_SOURCE_IDS or file_name in {f"{item}.json" for item in SEED_SOURCE_IDS})
