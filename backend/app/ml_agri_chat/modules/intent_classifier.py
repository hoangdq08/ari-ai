"""Cascade intent classifier for the chat endpoint.

Two-layer design:

- **Layer 1** (`_DeterministicClassifier`): pattern + verb-object rules. Free,
  ~0ms, deterministic, but limited. Handles the obvious ~80% of traffic.
- **Layer 2** (`_LLMIntentClassifier`): single short LLM call with strict JSON
  output. Catches code-switching, slang, ambiguous verb-object combos.
  ~1-2s on cache miss; results cached in a small LRU. Falls back to "pass to
  RAG" if the LLM is unreachable so traffic is never blocked by the
  classifier.

The public surface is `CascadeIntentClassifier` (instantiated once at module
import in `router.py`). It exposes `classify(question) -> IntentResult` and
`canned_response(intent) -> dict | None`.
"""

from __future__ import annotations

import json
import re
import threading
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal

from .llm_client import LocalLLMClient
from .prompt_guard import DISCLAIMER


# Canonical intent labels. Kept narrow on purpose; adding a new label means
# updating L1 rules, the LLM prompt enum, and `canned_response()`.
Intent = Literal[
    "agri_question",  # User asks something technical about coffee farming.
    "greeting",  # Hello / thanks / goodbye / capability questions.
    "social_chitchat",  # Invitations / small talk that may mention the crop.
    "out_of_scope",  # Off-topic (politics, stocks, weapons, personal life...).
]


@dataclass(frozen=True)
class IntentResult:
    label: Intent
    confidence: float
    source: str  # "l1_deterministic", "l1_cache", "l2_llm", "l2_cache", "l2_fallback"
    reason: str | None = None


# --------------------------------------------------------------------------
# Layer 1: deterministic rules
# --------------------------------------------------------------------------


# Crop / agriculture nouns. Stripped form (no diacritics, đ->d).
_CROP_NOUNS = {
    "ca phe", "cafe", "coffee", "cf",
    "lua", "rau", "che", "ho tieu", "tieu",
    "dieu", "sau rieng", "bo", "ca cao", "cacao", "mit",
    "vuon", "ray", "ruong", "trang trai", "nong nghiep",
    "cay trong", "cay", "giong", "phan bon", "sau benh",
    "benh cay", "thu hoach", "canh tac", "tuoi", "nang suat",
    "dat",
}

# Agriculture verbs - if the question pairs a crop with one of these, it is
# very likely a genuine farming question.
_AGRI_VERBS = {
    "trong", "tia", "ghep", "ban", "u",
    "tuoi", "bon", "phun", "ngua", "ngat", "diet",
    "phong tru", "phong", "kiem soat", "cham soc", "cai tao",
    "tai canh", "thu hoach", "thu hai", "che bien", "phoi",
    "say", "san phoi", "bao quan", "uom", "gieo", "san xuat",
    "chua", "tri", "khac phuc", "nhan biet", "nhan dien",
    "phat hien", "ngua benh", "kiem tra",
}

# Agriculture *topic* nouns. Even without an explicit verb, presence of one
# of these alongside a crop noun is a strong agri signal ("cây cà phê bị
# bệnh gì"). Multi-word entries match as substrings; single tokens are
# checked against the tokenised compact form to avoid false matches like
# "u" appearing inside "ru".
_AGRI_TOPIC_NOUNS = {
    "benh", "sau benh", "nam", "rep", "ri sat", "vi rut", "vi khuan",
    "dom mat cua", "than thu", "tuyen trung", "rep sap",
    "trieu chung", "vang la", "rung la", "rung qua",
    "phan bon", "phan", "npk", "kali", "ure",
    "thuoc bvtv", "thuoc tru sau", "thuoc tru nam",
    "giong", "tai canh",
    "hat giong", "cay con",
    "qua chin", "qua xanh", "hoa", "trai", "re", "than", "la",
    "vuon", "ray", "ruong",
}

# Social / chat verbs around a crop noun = invitation / smalltalk.
_SOCIAL_VERBS = {
    "di", "ra", "qua", "ru", "len", "ghe",
    "uong", "lam", "kieu", "kieu mot", "kieu mot ly", "kieu ly",
    "ly", "coc", "tach", "lam vai", "lam mot",
    "hen", "gap", "an", "nhau", "choi",
    "moi", "tu",
}

# Phrases that signal *invitation* / *smalltalk* even without a crop noun.
_SOCIAL_PHRASES = {
    "hen ho", "di choi", "di an", "di nhau", "lam vai ly",
    "ru di", "ru anh", "ru em", "moi em", "moi anh",
    "toi nay", "chieu nay", "sang nay", "trua nay",
    "ranh khong", "ranh ko", "co ranh",
}

# Topics that are clearly out of scope. Free keyword: any occurrence wins.
_OUT_OF_SCOPE_TERMS = {
    "chung khoan", "co phieu", "crypto", "coin", "forex",
    "bat dong san", "vu khi", "mat khau", "hack",
    "benh nguoi", "bac si", "luat su",
    "bong da", "the thao",
    "chinh tri", "thoi su",
}

# Greeting / thanks / goodbye / capability. Use *equality on compact form* so
# "chao ban dep trai" (an actual question) does not match "chao ban".
_GREETING_EQUAL = {
    "hi", "hello", "helo", "hey", "chao", "xin chao",
    "chao ban", "chao ai", "chao em", "chao anh",
}
_THANKS_EQUAL = {
    "cam on", "thanks", "thank you", "ok cam on", "oke cam on",
}
_GOODBYE_EQUAL = {
    "tam biet", "bye", "goodbye",
}
_CAPABILITY_CONTAINS = {
    "ban lam duoc gi", "co the lam gi", "huong dan su dung",
    "hoi gi duoc", "ban la ai", "nong tri ai la gi",
}

# Tokens that strongly indicate a question is asking about technique even
# when the verb is generic ("làm sao", "thế nào", "tại sao").
_TECHNIQUE_QUESTION_MARKERS = {
    "lam sao", "the nao", "ra sao", "tai sao", "vi sao",
    "khi nao", "bao nhieu", "bao lau", "bao gio",
    "lieu luong", "trieu chung", "nguyen nhan", "cach",
}


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    decomposed = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return without_marks.replace("đ", "d")


def _compact(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _contains_any(haystack: str, needles: set[str] | list[str]) -> bool:
    return any(needle in haystack for needle in needles)


def _matches_token_aware(compact: str, needles: set[str] | list[str]) -> bool:
    """Match short tokens (<=3 chars) as whole tokens to avoid substring
    false positives ("u" inside "ru"). Multi-word needles match as
    substring."""
    tokens = set(compact.split())
    for needle in needles:
        if " " in needle:
            if needle in compact:
                return True
        elif len(needle) <= 3:
            if needle in tokens:
                return True
        else:
            # Longer single-word needles: still substring-safe for compound
            # words (cham_soc vs chamsoc); test verified.
            if needle in compact:
                return True
    return False


class _DeterministicClassifier:
    """Layer 1. Returns an `IntentResult` with `confidence`:

    - 0.95 when the rules are unambiguous (e.g. exact greeting match, OOS
      keyword, crop + agri verb without social verb).
    - 0.6 when only weak signals (crop noun alone, no verb context).
    - 0.0 when nothing matched ("unknown" -> caller falls back to LLM).
    """

    def classify(self, question: str) -> IntentResult:
        normalized = _normalize(question)
        compact = _compact(normalized)

        # 1. Greeting/thanks/goodbye/capability - high confidence, no LLM needed.
        if compact in _GREETING_EQUAL:
            return IntentResult("greeting", 0.95, "l1_deterministic", "greeting")
        if compact in _THANKS_EQUAL:
            return IntentResult("greeting", 0.95, "l1_deterministic", "thanks")
        if compact in _GOODBYE_EQUAL:
            return IntentResult("greeting", 0.95, "l1_deterministic", "goodbye")
        if any(phrase in compact for phrase in _CAPABILITY_CONTAINS):
            return IntentResult("greeting", 0.95, "l1_deterministic", "capability")

        # 2. Out-of-scope keywords - high confidence reject.
        oos_hit = next((term for term in _OUT_OF_SCOPE_TERMS if term in normalized), None)
        if oos_hit:
            return IntentResult("out_of_scope", 0.95, "l1_deterministic", f"oos_term:{oos_hit}")

        # 3. Social phrases without crop noun (still social).
        social_phrase_hit = next((p for p in _SOCIAL_PHRASES if p in compact), None)

        # 4. Verb/object analysis around crop nouns.
        has_crop = _matches_token_aware(compact, _CROP_NOUNS)
        has_agri_verb = _matches_token_aware(compact, _AGRI_VERBS)
        has_agri_topic = _matches_token_aware(compact, _AGRI_TOPIC_NOUNS)
        has_social_verb = _matches_token_aware(compact, _SOCIAL_VERBS)
        has_technique_marker = _contains_any(compact, _TECHNIQUE_QUESTION_MARKERS)

        if has_crop and (has_agri_verb or has_agri_topic):
            # Trồng cà phê, bón phân cho cà phê, cây cà phê bị bệnh -> clearly farming.
            return IntentResult(
                "agri_question",
                0.95,
                "l1_deterministic",
                "crop+agri_verb_or_topic",
            )

        if has_crop and has_technique_marker and not has_social_verb:
            # "cà phê bị bệnh gì", "tại sao lá vàng" -> farming question.
            return IntentResult(
                "agri_question",
                0.9,
                "l1_deterministic",
                "crop+technique_marker",
            )

        if has_crop and (has_social_verb or social_phrase_hit):
            # "đi cà phê", "làm ly cà phê", "rủ đi cà phê chiều nay".
            # If technique markers ALSO present we are ambiguous -> fall to L2.
            if has_technique_marker:
                return IntentResult(
                    "agri_question",
                    0.0,
                    "l1_deterministic",
                    "ambiguous_crop+social_verb+technique",
                )
            return IntentResult(
                "social_chitchat",
                0.9,
                "l1_deterministic",
                f"crop+social_verb{'+'+social_phrase_hit if social_phrase_hit else ''}",
            )

        if social_phrase_hit and not has_crop:
            return IntentResult(
                "social_chitchat",
                0.9,
                "l1_deterministic",
                f"social_phrase:{social_phrase_hit}",
            )

        if has_crop and not has_social_verb:
            # Crop noun alone, no clear verb. Low confidence agri guess;
            # caller will fall to L2.
            return IntentResult(
                "agri_question",
                0.6,
                "l1_deterministic",
                "crop_only_weak",
            )

        # Nothing matched - unknown.
        return IntentResult("agri_question", 0.0, "l1_deterministic", "no_match")


# --------------------------------------------------------------------------
# Layer 2: LLM classifier
# --------------------------------------------------------------------------


_LLM_PROMPT_TEMPLATE = """Bạn là một bộ phân loại intent cho trợ lý nông nghiệp tiếng Việt về cây cà phê.

Chỉ trả về MỘT JSON object với schema sau, không kèm bất kỳ chữ nào khác:
{{"intent": "<một trong: agri_question | greeting | social_chitchat | out_of_scope>", "confidence": <số 0..1>, "reason": "<≤80 ký tự tiếng Việt giải thích ngắn>"}}

Định nghĩa intent:
- agri_question: câu hỏi kỹ thuật về cây cà phê / nông nghiệp (trồng, chăm, bệnh, thu hoạch, phân bón, giống...).
- greeting: chào hỏi, cảm ơn, tạm biệt, hỏi khả năng của trợ lý.
- social_chitchat: rủ rê, xã giao, hẹn hò, lời mời uống cà phê / đi chơi - có thể nhắc tới cây cà phê nhưng KHÔNG hỏi kỹ thuật.
- out_of_scope: ngoài nông nghiệp (chứng khoán, thời sự, đời tư, y tế, thể thao...).

Quy tắc:
- Nếu câu vừa rủ vừa hỏi kỹ thuật, ưu tiên agri_question.
- "đi cà phê", "uống cà phê", "làm ly cà phê" KHÔNG phải agri_question - đó là social_chitchat.
- "trồng cà phê", "cây cà phê bị bệnh", "bón phân cho cà phê" - là agri_question.

CÂU CẦN PHÂN LOẠI:
{question}

JSON:"""


_JSON_OBJECT_RE = re.compile(r"\{.*?\}", re.DOTALL)


class _LLMIntentClassifier:
    """Layer 2 calling an LLM with strict JSON output."""

    def __init__(self, llm_client: LocalLLMClient, *, timeout_seconds: float = 3.0):
        self._llm = llm_client
        self._timeout = timeout_seconds

    def classify(self, question: str) -> IntentResult:
        if not self._llm.is_enabled():
            return IntentResult(
                "agri_question",
                0.0,
                "l2_fallback",
                "llm_disabled",
            )

        prompt = _LLM_PROMPT_TEMPLATE.format(question=question[:500])
        result = self._llm.generate(
            prompt, temperature=0.0, timeout_override=self._timeout
        )
        if result.used_fallback or not result.text:
            return IntentResult(
                "agri_question",  # safe default: send to RAG, do not block.
                0.0,
                "l2_fallback",
                f"llm_unavailable: {result.error or 'no text'}",
            )

        parsed = self._parse_json(result.text)
        if parsed is None:
            return IntentResult(
                "agri_question",
                0.0,
                "l2_fallback",
                f"llm_invalid_json: {result.text[:80]!r}",
            )

        label = parsed.get("intent")
        if label not in {"agri_question", "greeting", "social_chitchat", "out_of_scope"}:
            return IntentResult(
                "agri_question",
                0.0,
                "l2_fallback",
                f"llm_unknown_label: {label!r}",
            )

        try:
            confidence = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        return IntentResult(
            label,  # type: ignore[arg-type]
            confidence,
            "l2_llm",
            str(parsed.get("reason", ""))[:120] or None,
        )

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any] | None:
        text = text.strip()
        # Strip a leading code fence if the model decided to wrap output.
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = _JSON_OBJECT_RE.search(text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


# --------------------------------------------------------------------------
# LRU cache + cascade
# --------------------------------------------------------------------------


class _LRUCache:
    """Small thread-safe LRU. Avoids pulling functools because the L2 input
    is the *normalised* question, not the raw object id."""

    def __init__(self, capacity: int = 256):
        self._cap = capacity
        self._store: OrderedDict[str, IntentResult] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> IntentResult | None:
        with self._lock:
            if key not in self._store:
                return None
            self._store.move_to_end(key)
            return self._store[key]

    def put(self, key: str, value: IntentResult) -> None:
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            while len(self._store) > self._cap:
                self._store.popitem(last=False)


# Confidence threshold below which L1 result is considered uncertain and the
# question is escalated to L2.
DEFAULT_L1_THRESHOLD = 0.7


class CascadeIntentClassifier:
    """Public entry point used by `router.py`."""

    def __init__(
        self,
        llm_client: LocalLLMClient | None = None,
        *,
        l1_confidence_threshold: float = DEFAULT_L1_THRESHOLD,
        cache_capacity: int = 256,
        llm_timeout_seconds: float = 3.0,
    ) -> None:
        self._l1 = _DeterministicClassifier()
        self._l2 = _LLMIntentClassifier(
            llm_client or LocalLLMClient(),
            timeout_seconds=llm_timeout_seconds,
        )
        self._threshold = l1_confidence_threshold
        self._cache = _LRUCache(cache_capacity)

    def classify(self, question: str) -> IntentResult:
        cache_key = _compact(_normalize(question))
        if not cache_key:
            return IntentResult("greeting", 0.95, "l1_deterministic", "empty_input")

        cached = self._cache.get(cache_key)
        if cached is not None:
            # Preserve source info but mark as cache hit so logs are obvious.
            return IntentResult(
                cached.label,
                cached.confidence,
                cached.source.replace("l2_llm", "l2_cache").replace(
                    "l1_deterministic", "l1_cache"
                ),
                cached.reason,
            )

        result = self._l1.classify(question)
        if result.confidence >= self._threshold:
            self._cache.put(cache_key, result)
            return result

        # Ambiguous or unknown - escalate.
        l2_result = self._l2.classify(question)
        if l2_result.source == "l2_llm":
            # Only cache trusted L2 outcomes.
            self._cache.put(cache_key, l2_result)
        return l2_result

    @staticmethod
    def canned_response(intent: Intent) -> dict[str, Any] | None:
        """Standard non-RAG response for an intent. Returns None for
        `agri_question` (caller should run RAG)."""
        if intent == "greeting":
            return {
                "answer": (
                    "Chào bạn, mình là Nông Trí AI. Bạn có thể hỏi ngắn gọn về vườn cà phê: "
                    "cây có triệu chứng gì, cần chăm sóc ra sao, bón phân/tưới nước thế nào, "
                    "hoặc nên kiểm tra vấn đề nào trước."
                ),
                "confidence_level": "cao",
                "sources": [],
                "safety_disclaimer": DISCLAIMER,
            }
        if intent == "social_chitchat":
            return {
                "answer": (
                    "Cảm ơn lời mời, nhưng mình là trợ lý chỉ làm việc về nông nghiệp cây cà phê thôi. "
                    "Bạn có câu hỏi nào về vườn cà phê, sâu bệnh, chăm sóc hay thu hoạch không?"
                ),
                "confidence_level": "cao",
                "sources": [],
                "safety_disclaimer": DISCLAIMER,
            }
        if intent == "out_of_scope":
            return {
                "answer": (
                    "Mình hiểu ý bạn, nhưng hiện Nông Trí AI được thiết kế để hỗ trợ trong phạm vi "
                    "nông nghiệp và cây cà phê. Nếu bạn muốn, hãy thử hỏi theo hướng vườn cà phê: "
                    "triệu chứng trên lá/quả/rễ, cách chăm sóc, bón phân, tưới nước, giống, thu hoạch."
                ),
                "confidence_level": "thap",
                "sources": [],
                "safety_disclaimer": DISCLAIMER,
            }
        return None
