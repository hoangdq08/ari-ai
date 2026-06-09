"""Filesystem / chunk-store helpers shared by ingest, research, and admin
endpoints.

These were originally module-private functions inside `router.py` with
leading underscores. They are still treated as internal (no public API
contract) but live in their own module so the per-domain route files can
import them without pulling the whole legacy router.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.ml_agri_chat.modules.data_ingestion import IngestedDocument
from app.ml_agri_chat.modules.document_chunking import chunk_document
from app.ml_agri_chat.modules.source_policy import source_review_decision, source_warnings
from app.ml_agri_chat.modules.taxonomy import enrich_metadata_with_taxonomy
from app.ml_agri_chat.modules.text_cleaning import clean_text

from ._shared import (
    CHUNKS_DIR,
    CLEANED_DIR,
    IMAGE_DATASET_DIR,
    KB_DIR,
    ML_PIPELINE_DIR,
    RAW_DIR,
    VECTOR_DIR,
    rag,
)


def read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def count_files(root: Path, suffixes: set[str]) -> int:
    if not root.exists():
        return 0
    return sum(1 for item in root.rglob("*") if item.is_file() and item.suffix.lower() in suffixes)


def count_json_chunks(root: Path) -> int:
    total = 0
    for path in root.glob("*.json"):
        data = read_json_file(path, default=[])
        if isinstance(data, list):
            total += len(data)
    return total


def chunk_previews(path: Path) -> list[dict]:
    chunks = read_json_file(path, default=[])
    if not isinstance(chunks, list):
        return []
    return [
        {
            "chunk_id": chunk.get("chunk_id"),
            "text": (chunk.get("text") or "")[:900],
            "char_count": len(chunk.get("text") or ""),
        }
        for chunk in chunks[:12]
    ]


def count_class_files(root: Path) -> dict[str, int]:
    if not root.exists():
        return {}
    counts: dict[str, int] = {}
    for class_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        counts[class_dir.name] = sum(1 for item in class_dir.rglob("*") if item.is_file() and item.name != ".gitkeep")
    return counts


def count_rejected(root: Path) -> dict[str, int]:
    if not root.exists():
        return {}
    counts: dict[str, int] = {}
    for reason_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        counts[reason_dir.name] = sum(1 for item in reason_dir.rglob("*") if item.is_file())
    return counts


def clear_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.name == ".gitkeep":
            continue
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            clear_directory(path)
            path.rmdir()


def existing_chunk_count(source_id: str) -> int:
    chunks = read_json_file(CHUNKS_DIR / f"{source_id}.json", default=[])
    return len(chunks) if isinstance(chunks, list) else 0


def duplicate_result(ingested: IngestedDocument) -> dict:
    return {
        "status": "duplicate",
        "source_id": ingested.source_id,
        "duplicate_of": ingested.duplicate_of or ingested.source_id,
        "chunks_created": existing_chunk_count(ingested.source_id),
        "chunks_added": 0,
        "message": "Source already exists; skipped raw/chunk/vector write.",
    }


def indexing_warnings(metadata: dict, raw_text: str, cleaned: str) -> list[str]:
    warnings = []
    if len(cleaned) < 500:
        warnings.append("cleaned_text_too_short")
    if len(raw_text) > 0 and len(cleaned) / len(raw_text) < 0.15:
        warnings.append("too_much_text_removed")
    warnings.extend(source_warnings(metadata.get("title"), metadata.get("url"), cleaned))
    return list(dict.fromkeys(warnings))


def indexing_quality_score(metadata: dict, raw_text: str, cleaned: str, warnings: list[str]) -> float:
    reliability = metadata.get("reliability_level") or "internet"
    score = 1.0
    score -= {"official": 0.0, "semi_official": 0.08, "manual": 0.05, "internet": 0.22}.get(reliability, 0.22)
    score -= min(0.5, len(warnings) * 0.08)
    if len(cleaned) < 500:
        score -= 0.18
    if len(raw_text) > 0 and len(cleaned) / len(raw_text) < 0.15:
        score -= 0.12
    return max(0.0, min(1.0, score))


def clean_chunk_store(source_id: str, raw_text: str, metadata: dict) -> dict:
    cleaned = clean_text(raw_text)
    with (CLEANED_DIR / f"{source_id}.txt").open("w", encoding="utf-8") as handle:
        handle.write(cleaned)

    enriched_metadata = enrich_metadata_with_taxonomy(metadata, cleaned)
    warnings = indexing_warnings(enriched_metadata, raw_text, cleaned)
    quality_score = indexing_quality_score(enriched_metadata, raw_text, cleaned, warnings)
    review = source_review_decision(enriched_metadata, quality_score, warnings)
    enriched_metadata.update(
        {
            "quality_score": round(quality_score, 3),
            "warnings": warnings,
            **review,
        }
    )
    chunks = chunk_document(cleaned, enriched_metadata)
    chunk_dicts = [chunk.to_dict() for chunk in chunks]
    with (CHUNKS_DIR / f"{source_id}.json").open("w", encoding="utf-8") as handle:
        json.dump(chunk_dicts, handle, ensure_ascii=False, indent=2)

    added = 0
    if review["indexing_status"] == "indexed":
        added = rag.add_chunks(chunk_dicts)
    return {
        "status": "ingested",
        "source_id": source_id,
        "chunks_created": len(chunks),
        "chunks_added": added,
        "review_status": review["review_status"],
        "indexing_status": review["indexing_status"],
        "quality_score": round(quality_score, 3),
        "warnings": warnings,
    }


def chunks_for_trusted_rebuild(source_id: str, chunks: object) -> tuple[list[dict], dict]:
    if not isinstance(chunks, list) or not chunks:
        return [], {"indexing_status": "held_for_review", "review_status": "needs_review"}
    valid_chunks = [chunk for chunk in chunks if isinstance(chunk, dict)]
    if not valid_chunks:
        return [], {"indexing_status": "held_for_review", "review_status": "needs_review"}

    metadata = dict(valid_chunks[0].get("metadata") or {})
    if metadata.get("indexing_status") == "indexed" or metadata.get("review_status") == "approved":
        return valid_chunks, {"indexing_status": "indexed", "review_status": "approved"}
    if metadata.get("indexing_status") == "blocked" or metadata.get("review_status") == "rejected":
        return [], {"indexing_status": "blocked", "review_status": "rejected"}
    if metadata.get("indexing_status") == "held_for_review" or metadata.get("review_status") == "needs_review":
        return [], {"indexing_status": "held_for_review", "review_status": "needs_review"}

    joined_text = "\n".join(str(chunk.get("text") or "") for chunk in valid_chunks)
    warnings = indexing_warnings(metadata, "", joined_text)
    quality_score = indexing_quality_score(metadata, "", joined_text, warnings)
    decision = source_review_decision(metadata, quality_score, warnings)
    if decision["indexing_status"] != "indexed":
        return [], decision

    enriched_chunks = []
    for chunk in valid_chunks:
        chunk_copy = dict(chunk)
        chunk_metadata = dict(chunk_copy.get("metadata") or {})
        chunk_metadata.update(
            {
                "source_id": chunk_metadata.get("source_id") or source_id,
                "quality_score": round(quality_score, 3),
                "warnings": warnings,
                **decision,
            }
        )
        chunk_copy["metadata"] = chunk_metadata
        enriched_chunks.append(chunk_copy)
    return enriched_chunks, decision


def seed_knowledge_base_if_needed() -> None:
    if rag.sources():
        return
    for path in sorted(KB_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            item = json.load(handle)
        metadata = {
            "source_id": path.stem,
            "source_type": item.get("source_type", "manual"),
            "title": item.get("title", path.stem),
            "file_name": path.name,
            "url": None,
            "page": None,
            "reliability_level": item.get("reliability_level", "manual"),
            "seed_sample": True,
        }
        clean_chunk_store(path.stem, item.get("text", ""), metadata)


def ensure_taxonomy_labels() -> None:
    changed = False
    chunk_dicts: list[dict] = []
    for path in sorted(CHUNKS_DIR.glob("*.json")):
        chunks = read_json_file(path, default=[])
        if not isinstance(chunks, list):
            continue
        file_changed = False
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            if not metadata.get("category"):
                enriched = enrich_metadata_with_taxonomy(metadata, chunk.get("text", ""))
                chunk["metadata"] = enriched
                file_changed = True
        if file_changed:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(chunks, handle, ensure_ascii=False, indent=2)
            changed = True
        indexable, _decision = chunks_for_trusted_rebuild(path.stem, chunks)
        chunk_dicts.extend(indexable)
    if changed and chunk_dicts:
        rag.rebuild(chunk_dicts)


def ops_pipeline_status() -> dict:
    raw_docs = count_files(RAW_DIR, {".json", ".txt", ".pdf", ".docx", ".html", ".htm"})
    cleaned_docs = count_files(CLEANED_DIR, {".txt"})
    chunk_files = len(list(CHUNKS_DIR.glob("*.json")))
    vector_chunks = len(read_json_file(VECTOR_DIR / "chunks.json", default=[]))
    raw_images = sum(count_class_files(IMAGE_DATASET_DIR / "raw").values())
    clean_images = sum(count_class_files(IMAGE_DATASET_DIR / "cleaned").values())
    rejected_images = sum(count_rejected(IMAGE_DATASET_DIR / "rejected").values())
    model_path = ML_PIPELINE_DIR / "models" / "coffee_disease_model.keras"
    label_map_path = ML_PIPELINE_DIR / "models" / "label_map.json"
    return {
        "rag_chunking": [
            {"step": "raw_documents", "label": "Raw documents", "count": raw_docs, "status": "done" if raw_docs else "waiting"},
            {"step": "cleaned_documents", "label": "Cleaned text", "count": cleaned_docs, "status": "done" if cleaned_docs else "waiting"},
            {"step": "chunk_files", "label": "Chunk files", "count": chunk_files, "status": "done" if chunk_files else "waiting"},
            {"step": "vector_chunks", "label": "Vector chunks", "count": vector_chunks, "status": "done" if vector_chunks else "waiting"},
        ],
        "vision_training": [
            {"step": "raw_images", "label": "Raw images", "count": raw_images, "status": "done" if raw_images else "waiting"},
            {"step": "clean_images", "label": "Cleaned images", "count": clean_images, "status": "done" if clean_images else "waiting"},
            {"step": "rejected_images", "label": "Rejected images", "count": rejected_images, "status": "review" if rejected_images else "waiting"},
            {"step": "model_export", "label": "Model artifact", "count": int(model_path.exists()), "status": "done" if model_path.exists() and label_map_path.exists() else "placeholder"},
        ],
    }
