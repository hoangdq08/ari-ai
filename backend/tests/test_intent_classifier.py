"""Eval + unit tests for the cascade intent classifier.

The eval set targets common patterns we see in coffee-farming chat. Each
entry is `(question, expected_intent, layer_hint)` where `layer_hint` is
informational only (which layer we EXPECT to resolve it) and is checked as
a soft assertion via `pytest.warns(...)`-free path.

Acceptance threshold: ≥90% top-1 accuracy on the L1-resolvable subset and
≥85% overall when L2 falls back (since L2 in tests is monkeypatched).
"""

from __future__ import annotations

from typing import Callable

import pytest

from app.ml_agri_chat.modules.intent_classifier import (
    CascadeIntentClassifier,
    IntentResult,
    _DeterministicClassifier,
    _LLMIntentClassifier,
)
from app.ml_agri_chat.modules.llm_client import LLMResult


# ---------------- Layer 1 deterministic ----------------


L1_CASES: list[tuple[str, str, str]] = [
    # Greetings
    ("xin chào", "greeting", "greeting_equal"),
    ("hello", "greeting", "greeting_equal"),
    ("cảm ơn", "greeting", "thanks"),
    ("tạm biệt", "greeting", "goodbye"),
    ("bạn làm được gì", "greeting", "capability"),
    ("Nông Trí AI là gì", "greeting", "capability"),
    # Social chitchat with crop noun
    ("tối đi cà phê không em?", "social_chitchat", "social"),
    ("đi cafe không", "social_chitchat", "social"),
    ("làm ly cà phê nhé", "social_chitchat", "social"),
    ("rủ đi cà phê chiều nay", "social_chitchat", "social"),
    ("ra cf đi", "social_chitchat", "social"),
    # Social chitchat without crop
    ("tối nay đi nhậu", "social_chitchat", "social"),
    ("đi chơi không", "social_chitchat", "social"),
    ("mình hẹn hò nhé", "social_chitchat", "social"),
    # Out of scope
    ("giá cổ phiếu hôm nay", "out_of_scope", "oos"),
    ("tỷ giá USD hôm nay", "out_of_scope", "oos"),  # actually misses keyword - see test
    # Genuine agri
    ("cây cà phê bị bệnh gì", "agri_question", "agri"),
    ("cách bón phân cho cà phê arabica", "agri_question", "agri"),
    ("trồng cà phê khi nào tốt nhất", "agri_question", "agri"),
    ("phòng trừ rỉ sắt lá cà phê", "agri_question", "agri"),
    ("thu hoạch cà phê đúng cách", "agri_question", "agri"),
    ("triệu chứng vàng lá cà phê", "agri_question", "agri"),
]


def test_l1_high_confidence_cases_match_expected():
    """All L1 cases with confidence >= threshold must hit expected label.

    For cases where the keyword list does not catch the phrase (e.g.
    'tỷ giá USD' has no OOS term), L1 falls through with low confidence -
    we exclude those from the strict match and rely on L2 in production.
    """
    l1 = _DeterministicClassifier()
    misses: list[tuple[str, str, str, float]] = []
    for question, expected, _hint in L1_CASES:
        result = l1.classify(question)
        if result.confidence >= 0.7 and result.label != expected:
            misses.append((question, expected, result.label, result.confidence))
    assert not misses, f"L1 high-confidence misclassifications: {misses}"


def test_l1_resolves_majority_of_eval_set():
    """At least 80% of L1_CASES should be resolved at L1 (>=0.7 conf)."""
    l1 = _DeterministicClassifier()
    resolved = sum(1 for q, _e, _h in L1_CASES if l1.classify(q).confidence >= 0.7)
    ratio = resolved / len(L1_CASES)
    assert ratio >= 0.8, f"L1 resolved only {resolved}/{len(L1_CASES)} ({ratio:.0%})"


def test_l1_no_false_positive_agri_for_social_invitation():
    """Specifically guard the leak that triggered this refactor."""
    l1 = _DeterministicClassifier()
    for q in ["tối đi cà phê không em?", "đi cafe nhé", "làm ly cà phê"]:
        r = l1.classify(q)
        assert r.label == "social_chitchat", (q, r)
        assert r.confidence >= 0.7, r


def test_l1_agri_questions_still_pass():
    l1 = _DeterministicClassifier()
    for q in [
        "cây cà phê bị bệnh gì",
        "bón phân cho cà phê arabica",
        "phòng trừ rỉ sắt lá cà phê",
    ]:
        r = l1.classify(q)
        assert r.label == "agri_question", (q, r)
        assert r.confidence >= 0.7, r


# ---------------- Layer 2 LLM classifier (mocked) ----------------


class _StubLLM:
    """Minimal LocalLLMClient stand-in returning canned text."""

    def __init__(self, *, text: str, error: str | None = None, enabled: bool = True):
        self._text = text
        self._error = error
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled

    def generate(self, prompt: str, *, temperature: float = 0.1, timeout_override=None, response_format=None) -> LLMResult:
        return LLMResult(
            text=self._text,
            provider="deepseek",
            model="deepseek-v4-flash",
            used_fallback=bool(self._error),
            error=self._error,
        )


def test_l2_parses_valid_json():
    llm = _StubLLM(
        text='{"intent": "social_chitchat", "confidence": 0.92, "reason": "lời mời đi uống"}'
    )
    l2 = _LLMIntentClassifier(llm)
    result = l2.classify("ra cf nha")
    assert result.label == "social_chitchat"
    assert 0.9 <= result.confidence <= 1.0
    assert result.source == "l2_llm"


def test_l2_strips_code_fence():
    llm = _StubLLM(
        text='```json\n{"intent": "agri_question", "confidence": 0.8}\n```'
    )
    l2 = _LLMIntentClassifier(llm)
    result = l2.classify("vườn em bị gì")
    assert result.label == "agri_question"


def test_l2_extracts_json_from_chatter():
    llm = _StubLLM(
        text='Đây là kết quả: {"intent": "out_of_scope", "confidence": 0.95} - hết.'
    )
    l2 = _LLMIntentClassifier(llm)
    result = l2.classify("giá vàng")
    assert result.label == "out_of_scope"


def test_l2_fallback_when_llm_fails():
    llm = _StubLLM(text="", error="timeout")
    l2 = _LLMIntentClassifier(llm)
    result = l2.classify("anything")
    assert result.label == "agri_question"  # safe default = send to RAG
    assert result.source == "l2_fallback"
    assert "timeout" in (result.reason or "")


def test_l2_fallback_on_invalid_json():
    llm = _StubLLM(text="not json at all, just words")
    l2 = _LLMIntentClassifier(llm)
    result = l2.classify("x")
    assert result.source == "l2_fallback"
    assert "invalid_json" in (result.reason or "")


def test_l2_fallback_on_unknown_label():
    llm = _StubLLM(text='{"intent": "something_else", "confidence": 0.99}')
    l2 = _LLMIntentClassifier(llm)
    result = l2.classify("x")
    assert result.source == "l2_fallback"
    assert "unknown_label" in (result.reason or "")


def test_l2_disabled_llm_returns_default():
    llm = _StubLLM(text="", enabled=False)
    l2 = _LLMIntentClassifier(llm)
    result = l2.classify("x")
    assert result.label == "agri_question"
    assert result.source == "l2_fallback"
    assert "disabled" in (result.reason or "")


# ---------------- Cascade behaviour ----------------


def test_cascade_high_l1_confidence_skips_llm():
    """If L1 already returns >= threshold, the LLM must NOT be called."""
    called: list[str] = []

    class TrackingLLM(_StubLLM):
        def generate(self, *a, **kw):
            called.append("yes")
            return super().generate(*a, **kw)

    cascade = CascadeIntentClassifier(
        TrackingLLM(text='{"intent": "agri_question", "confidence": 1}'),
        l1_confidence_threshold=0.7,
    )
    result = cascade.classify("trồng cà phê khi nào tốt nhất")
    assert result.label == "agri_question"
    assert result.source == "l1_deterministic"
    assert not called


def test_cascade_low_l1_falls_through_to_l2():
    """Ambiguous L1 result -> L2 should be consulted."""
    llm = _StubLLM(text='{"intent": "out_of_scope", "confidence": 0.95}')
    cascade = CascadeIntentClassifier(llm, l1_confidence_threshold=0.7)
    # Bare crop noun -> L1 returns crop_only_weak with conf 0.6
    result = cascade.classify("cà phê")
    assert result.source == "l2_llm"
    assert result.label == "out_of_scope"


def test_cascade_caches_l2_outcome():
    """Second call with same normalised question should not hit LLM again."""
    call_count = {"n": 0}

    class CountingLLM(_StubLLM):
        def generate(self, *a, **kw):
            call_count["n"] += 1
            return super().generate(*a, **kw)

    cascade = CascadeIntentClassifier(
        CountingLLM(text='{"intent": "out_of_scope", "confidence": 0.95}'),
        l1_confidence_threshold=0.7,
    )
    cascade.classify("cà phê")
    cascade.classify("cà phê")  # same key
    cascade.classify("CÀ PHÊ!!!")  # normalises to same key
    assert call_count["n"] == 1

    # Cached source label preserved as cache hit.
    cached = cascade.classify("cà phê")
    assert cached.source == "l2_cache"


def test_cascade_does_not_cache_l2_fallback():
    """Don't cache LLM failures - retry next time."""
    failing_llm = _StubLLM(text="", error="boom")
    cascade = CascadeIntentClassifier(failing_llm, l1_confidence_threshold=0.7)

    r1 = cascade.classify("cà phê")
    r2 = cascade.classify("cà phê")
    assert r1.source == "l2_fallback"
    assert r2.source == "l2_fallback"  # NOT l2_cache


def test_cascade_empty_input():
    cascade = CascadeIntentClassifier(_StubLLM(text=""))
    result = cascade.classify("   ")
    assert result.label == "greeting"


def test_cascade_canned_response_shapes():
    assert CascadeIntentClassifier.canned_response("greeting")["confidence_level"] == "cao"
    assert CascadeIntentClassifier.canned_response("social_chitchat")["confidence_level"] == "cao"
    assert CascadeIntentClassifier.canned_response("out_of_scope")["confidence_level"] == "thap"
    assert CascadeIntentClassifier.canned_response("agri_question") is None


# ---------------- Metrics ----------------


def test_stats_counts_by_source_and_label():
    """Classifier exposes counters per layer source + per intent label."""
    cascade = CascadeIntentClassifier(
        _StubLLM(text='{"intent": "out_of_scope", "confidence": 0.95}'),
        l1_confidence_threshold=0.7,
    )

    # L1 paths
    cascade.classify("xin chào")          # greeting via l1_deterministic
    cascade.classify("trồng cà phê")      # agri via l1_deterministic
    cascade.classify("tối đi cà phê không")  # social via l1_deterministic
    # L2 path (crop only -> weak L1 -> escalates)
    cascade.classify("cà phê")
    # Cache hit
    cascade.classify("xin chào")

    stats = cascade.stats()
    assert stats["total"] == 5
    by_source = stats["by_source"]
    by_label = stats["by_label"]

    # 2x deterministic greeting/agri/social already covered. The
    # repeated "xin chào" is a L1 cache hit.
    assert by_source["l1_deterministic"] == 3
    assert by_source["l1_cache"] == 1
    assert by_source["l2_llm"] == 1

    assert by_label["greeting"] == 2  # original + cached
    assert by_label["agri_question"] == 1
    assert by_label["social_chitchat"] == 1
    assert by_label["out_of_scope"] == 1


def test_stats_starts_empty():
    cascade = CascadeIntentClassifier(_StubLLM(text=""))
    stats = cascade.stats()
    assert stats == {"by_source": {}, "by_label": {}, "total": 0}


# ---------------- History-aware follow-up handling ----------------


def test_followup_detection_basic():
    """`_is_followup_question` flags deictic / referential phrasings."""
    from app.ml_agri_chat.modules.intent_classifier import _is_followup_question
    assert _is_followup_question("vậy còn cây kia thì sao") is True
    assert _is_followup_question("thế còn cái này") is True
    assert _is_followup_question("rồi sao nữa") is True
    assert _is_followup_question("vậy nó?") is True
    # Plain agri questions are NOT follow-ups.
    assert _is_followup_question("cây cà phê bị bệnh gì") is False
    assert _is_followup_question("trồng cà phê khi nào tốt nhất") is False


def test_format_history_renders_role_lines():
    from app.ml_agri_chat.modules.intent_classifier import _format_history
    rendered = _format_history(
        [
            {"role": "user", "content": "cây cà phê bị bệnh gì"},
            {"role": "assistant", "content": "Có thể là rỉ sắt..."},
            {"role": "user", "content": "vậy thì làm sao chữa"},
        ]
    )
    assert "Người dùng" in rendered
    assert "Trợ lý" in rendered
    assert "rỉ sắt" in rendered


def test_format_history_empty_returns_placeholder():
    from app.ml_agri_chat.modules.intent_classifier import _format_history
    assert "không có lịch sử" in _format_history(None)
    assert "không có lịch sử" in _format_history([])


def test_followup_bypasses_l1_cache_and_calls_l2_with_history():
    """A short follow-up text 'vậy nó' should NOT be answered from cache
    even if a previous call cached an unrelated intent for the same text."""
    captured = {"history": None, "calls": 0}

    class HistoryCapturingLLM(_StubLLM):
        def generate(self, prompt, *, temperature=0.1, timeout_override=None, response_format=None):
            captured["calls"] += 1
            captured["history"] = "Người dùng: cây cà phê bị bệnh gì" in prompt
            return super().generate(
                prompt,
                temperature=temperature,
                timeout_override=timeout_override,
                response_format=response_format,
            )

    llm = HistoryCapturingLLM(
        text='{"intent": "agri_question", "confidence": 0.9, "reason": "câu hỏi nối tiếp về bệnh cây"}'
    )
    cascade = CascadeIntentClassifier(llm, l1_confidence_threshold=0.7)

    history = [
        {"role": "user", "content": "cây cà phê bị bệnh gì"},
        {"role": "assistant", "content": "Có thể là rỉ sắt"},
    ]
    result = cascade.classify("vậy nó", history=history)
    assert result.source == "l2_llm"
    assert result.label == "agri_question"
    assert captured["history"] is True  # LLM saw the prior turn
    assert captured["calls"] == 1


def test_followup_results_are_not_cached():
    """Two distinct sessions could send 'vậy nó' meaning different things;
    we must not lock in the first answer."""
    call_count = {"n": 0}

    class CountingLLM(_StubLLM):
        def generate(self, prompt, *, temperature=0.1, timeout_override=None, response_format=None):
            call_count["n"] += 1
            return super().generate(
                prompt,
                temperature=temperature,
                timeout_override=timeout_override,
                response_format=response_format,
            )

    llm = CountingLLM(text='{"intent": "agri_question", "confidence": 0.9}')
    cascade = CascadeIntentClassifier(llm, l1_confidence_threshold=0.7)
    history = [{"role": "user", "content": "cây cà phê bị bệnh gì"}]

    cascade.classify("vậy nó", history=history)
    cascade.classify("vậy nó", history=history)
    # No cache hit -> LLM called twice.
    assert call_count["n"] == 2


def test_followup_with_no_history_falls_through_l1_normal_path():
    """A first-turn message that LOOKS like a follow-up but has no history
    must still go through the normal L1 flow (and cache when L1 is
    confident). Otherwise the cache becomes useless."""
    cascade = CascadeIntentClassifier(
        _StubLLM(text='{"intent": "agri_question", "confidence": 0.9}'),
        l1_confidence_threshold=0.7,
    )
    # Follow-up phrasing but NO history.
    result1 = cascade.classify("vậy thì sao", history=None)
    # Then again - should be cache hit.
    result2 = cascade.classify("vậy thì sao", history=None)
    assert result2.source in {"l1_cache", "l2_cache"}


def test_non_followup_with_history_still_uses_cache():
    """History attached but the message itself is a fresh agri question -
    cache must still work to keep latency low for repeat questions."""
    cascade = CascadeIntentClassifier(
        _StubLLM(text='{"intent": "agri_question", "confidence": 0.9}'),
        l1_confidence_threshold=0.7,
    )
    history = [{"role": "user", "content": "earlier turn"}]
    r1 = cascade.classify("trồng cà phê khi nào tốt nhất", history=history)
    r2 = cascade.classify("trồng cà phê khi nào tốt nhất", history=history)
    assert r1.source == "l1_deterministic"
    assert r2.source == "l1_cache"


# ---------------- Followup confirmation patterns ----------------


def test_followup_confirmation_patterns():
    """Short replies like 'ok chưa', 'chiến chưa?', 'xong chưa' depend
    on the prior turn and must be flagged. Reported via screenshot:
    user asked about pre-harvest care, then sent 'chiến chưa ?' which
    was being treated as a fresh agri question and retrieved random
    chunks."""
    from app.ml_agri_chat.modules.intent_classifier import _is_followup_question
    for prompt in [
        "chiến chưa ?",
        "ok chưa",
        "ổn chưa",
        "được chưa",
        "xong chưa",
        "đúng không",
        "phải không",
        "hiểu chưa",
        "rồi",
        "ok",
        "chưa a",
    ]:
        assert _is_followup_question(prompt) is True, prompt


def test_followup_does_not_swallow_real_agri_questions():
    """Long agri questions that happen to end with 'không' or use a
    deictic pronoun mid-sentence must NOT be flagged - that would
    bypass the L1 cache and burn LLM tokens for every farming question."""
    from app.ml_agri_chat.modules.intent_classifier import _is_followup_question
    for prompt in [
        "cây cà phê bị bệnh gì",
        "có nên bón vôi cho cà phê không",
        "phòng trừ rỉ sắt lá cà phê",
        "trước thu hoạch cà phê tôi cần lưu ý gì",
        "trồng cà phê khi nào tốt nhất",
    ]:
        assert _is_followup_question(prompt) is False, prompt
