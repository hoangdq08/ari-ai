"""Lightweight per-route latency middleware.

Captures wall-clock duration of each request and keeps a bounded ring buffer
of samples. `/admin/ops-events` surfaces p50/p95 so the KPI in
`docs/planning/he-thong-ai-nong-nghiep.pptx` (slide 13, "Latency p50 ≤ 3.0s")
has a concrete metric to demo, instead of being a slogan.

Sampling strategy:
- One sample per request, key = HTTP method + route path template.
- Ring buffer capped (env `NONGTRI_LATENCY_BUFFER_SIZE`, default 2000).
- Computed on demand via `latency_report()` so we never lock during request.
"""

from __future__ import annotations

import bisect
import os
import time
from collections import deque
from threading import RLock
from typing import Any, Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_BUFFER_SIZE = int(os.getenv("NONGTRI_LATENCY_BUFFER_SIZE", "2000"))
_samples: Deque[dict[str, Any]] = deque(maxlen=_BUFFER_SIZE)
# Stage buffer is a separate ring so per-stage timings (intent / retrieval
# / answer) do not crowd out per-route samples. Sized smaller because each
# /chat call writes ~3 stage entries; we still want a few thousand chats
# worth of history for tuning.
_STAGE_BUFFER_SIZE = int(os.getenv("NONGTRI_LATENCY_STAGE_BUFFER_SIZE", "6000"))
_stage_samples: Deque[dict[str, Any]] = deque(maxlen=_STAGE_BUFFER_SIZE)
_lock = RLock()


def record_sample(route: str, method: str, duration_ms: float, status_code: int) -> None:
    with _lock:
        _samples.append(
            {
                "route": route,
                "method": method,
                "duration_ms": round(duration_ms, 2),
                "status_code": status_code,
            }
        )


def record_stage(stage: str, duration_ms: float, *, route: str = "/chat") -> None:
    """Append a per-stage timing sample.

    Used by the chat endpoint to break down which sub-step (intent
    classification, retrieval, LLM advisor) dominates the per-request
    budget. The same percentile machinery in `latency_report()` is reused
    via `stage_report()`.
    """
    with _lock:
        _stage_samples.append(
            {
                "stage": stage,
                "route": route,
                "duration_ms": round(duration_ms, 2),
            }
        )


class StageTimer:
    """`with StageTimer("intent"):` records elapsed wall-clock on exit.

    No-op if `record` is set to False (e.g. test isolation).
    """

    def __init__(self, stage: str, *, route: str = "/chat", record: bool = True):
        self._stage = stage
        self._route = route
        self._record = record
        self._started: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> "StageTimer":
        self._started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed_ms = (time.perf_counter() - self._started) * 1000.0
        if self._record:
            record_stage(self._stage, self.elapsed_ms, route=self._route)


def latency_report() -> dict[str, Any]:
    """Return p50 / p95 / max / count grouped by route."""
    with _lock:
        snapshot = list(_samples)

    grouped: dict[str, list[float]] = {}
    for sample in snapshot:
        key = f"{sample['method']} {sample['route']}"
        grouped.setdefault(key, []).append(sample["duration_ms"])

    routes = []
    overall: list[float] = []
    for key, durations in grouped.items():
        durations_sorted = sorted(durations)
        overall.extend(durations_sorted)
        routes.append(
            {
                "route": key,
                "count": len(durations_sorted),
                "p50_ms": _percentile(durations_sorted, 50),
                "p95_ms": _percentile(durations_sorted, 95),
                "max_ms": durations_sorted[-1],
            }
        )

    overall_sorted = sorted(overall)
    return {
        "samples": len(overall_sorted),
        "p50_ms": _percentile(overall_sorted, 50) if overall_sorted else 0,
        "p95_ms": _percentile(overall_sorted, 95) if overall_sorted else 0,
        "max_ms": overall_sorted[-1] if overall_sorted else 0,
        "by_route": sorted(routes, key=lambda item: -item["count"]),
    }


def _percentile(sorted_values: list[float], pct: int) -> float:
    if not sorted_values:
        return 0.0
    if pct <= 0:
        return sorted_values[0]
    if pct >= 100:
        return sorted_values[-1]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return round(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight, 2)


def reset() -> None:
    """Clear all collected samples (used by tests + admin reset path)."""
    with _lock:
        _samples.clear()
        _stage_samples.clear()


def stage_report() -> dict[str, Any]:
    """Same shape as `latency_report()` but grouped by per-stage labels."""
    with _lock:
        snapshot = list(_stage_samples)

    grouped: dict[str, list[float]] = {}
    for sample in snapshot:
        grouped.setdefault(sample["stage"], []).append(sample["duration_ms"])

    stages = []
    for stage, durations in grouped.items():
        durations_sorted = sorted(durations)
        stages.append(
            {
                "stage": stage,
                "count": len(durations_sorted),
                "p50_ms": _percentile(durations_sorted, 50),
                "p95_ms": _percentile(durations_sorted, 95),
                "max_ms": durations_sorted[-1],
            }
        )
    return {
        "samples": len(snapshot),
        "by_stage": sorted(stages, key=lambda item: -item["count"]),
    }


class LatencyMiddleware(BaseHTTPMiddleware):
    """ASGI middleware: wraps every request, records duration."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        started = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        # `request.scope["route"]` is set by Starlette/FastAPI once the route is matched.
        route_obj = request.scope.get("route")
        route_path = getattr(route_obj, "path", request.url.path)
        record_sample(
            route=route_path,
            method=request.method,
            duration_ms=elapsed_ms,
            status_code=response.status_code,
        )
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response


__all__ = [
    "LatencyMiddleware",
    "record_sample",
    "record_stage",
    "StageTimer",
    "latency_report",
    "stage_report",
    "reset",
]
