"""Tests for the shared latency machinery (per-route + per-stage)."""

from __future__ import annotations

import time

from app.shared.latency import (
    StageTimer,
    record_stage,
    reset,
    stage_report,
)


def setup_function():
    reset()


def test_stage_timer_records_elapsed():
    with StageTimer("intent") as timer:
        time.sleep(0.005)
    assert timer.elapsed_ms >= 4.0  # 5ms with a little slack for jitter
    report = stage_report()
    assert report["samples"] == 1
    by_stage = {item["stage"]: item for item in report["by_stage"]}
    assert "intent" in by_stage
    assert by_stage["intent"]["count"] == 1


def test_stage_timer_skip_record_flag():
    """`record=False` lets call sites time work without polluting metrics."""
    with StageTimer("intent", record=False) as timer:
        pass
    assert timer.elapsed_ms >= 0
    assert stage_report()["samples"] == 0


def test_record_stage_groups_by_label():
    for value in [10.0, 20.0, 30.0, 40.0, 50.0]:
        record_stage("retrieval", value)
    for value in [100.0, 200.0]:
        record_stage("advisor", value)

    report = stage_report()
    by_stage = {item["stage"]: item for item in report["by_stage"]}
    assert report["samples"] == 7
    assert by_stage["retrieval"]["count"] == 5
    assert by_stage["retrieval"]["p50_ms"] == 30.0
    assert by_stage["retrieval"]["max_ms"] == 50.0
    assert by_stage["advisor"]["count"] == 2


def test_reset_clears_both_route_and_stage_samples():
    record_stage("intent", 1.0)
    assert stage_report()["samples"] == 1
    reset()
    assert stage_report()["samples"] == 0
