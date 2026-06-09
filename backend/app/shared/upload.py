"""Shared upload helpers — size-capped streaming reads for FastAPI `UploadFile`.

Avoids OOM when accepting client-uploaded files by enforcing a hard byte limit
without buffering the whole stream first.
"""

from __future__ import annotations

import os

from fastapi import HTTPException, UploadFile


DEFAULT_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_DOCUMENT_BYTES = 25 * 1024 * 1024  # 25MB
DEFAULT_AUDIO_BYTES = 25 * 1024 * 1024  # 25MB


def max_image_bytes() -> int:
    return int(os.getenv("NONGTRI_MAX_IMAGE_BYTES", str(DEFAULT_IMAGE_BYTES)))


def max_document_bytes() -> int:
    return int(os.getenv("NONGTRI_MAX_DOCUMENT_BYTES", str(DEFAULT_DOCUMENT_BYTES)))


def max_audio_bytes() -> int:
    return int(os.getenv("NONGTRI_MAX_AUDIO_BYTES", str(DEFAULT_AUDIO_BYTES)))


async def read_upload_capped(file: UploadFile, max_bytes: int, kind: str) -> bytes:
    """Read `file` in chunks; raise 413 if total bytes exceed `max_bytes`.

    Parameters
    ----------
    file: FastAPI UploadFile to consume.
    max_bytes: hard upper bound on payload size (bytes).
    kind: short label used in the error response (e.g. "Image", "Document").
    """
    chunks: list[bytes] = []
    total = 0
    chunk_size = 1 << 20  # 1MB
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"{kind} too large (limit {max_bytes // (1024 * 1024)}MB).",
            )
        chunks.append(chunk)
    return b"".join(chunks)
