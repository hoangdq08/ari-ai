from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def chunk_document(
    text: str,
    metadata: dict[str, Any],
    max_chars: int = 1200,
    overlap_chars: int = 160,
) -> list[DocumentChunk]:
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= 40]
    chunks: list[DocumentChunk] = []
    current = ""

    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(_make_chunk(current, metadata))
            current = current[-overlap_chars:] if overlap_chars and len(current) > overlap_chars else ""
        current = f"{current}\n\n{paragraph}".strip() if current else paragraph

    if current:
        chunks.append(_make_chunk(current, metadata))
    return chunks


def _make_chunk(text: str, metadata: dict[str, Any]) -> DocumentChunk:
    enriched = {
        "source_id": metadata.get("source_id") or str(uuid4()),
        "source_type": metadata.get("source_type", "manual"),
        "title": metadata.get("title", "Tài liệu chưa đặt tên"),
        "url": metadata.get("url"),
        "file_name": metadata.get("file_name"),
        "page": metadata.get("page"),
        "crawled_at": metadata.get("crawled_at") or datetime.now(timezone.utc).isoformat(),
        "reliability_level": metadata.get("reliability_level", "manual"),
        "category": metadata.get("category"),
        "category_label": metadata.get("category_label"),
        "category_confidence": metadata.get("category_confidence"),
        "category_terms": metadata.get("category_terms", []),
    }
    return DocumentChunk(chunk_id=str(uuid4()), text=text, metadata=enriched)
