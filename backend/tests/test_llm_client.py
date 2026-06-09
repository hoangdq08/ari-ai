"""Unit tests for the LLM client facade + fallback chain.

Covers:
- Primary + fallback selection and default behaviour
- Provider-specific generate() success / failure modes
- Fallback fired (cloud fail -> local served)
- Both providers down (aggregated error)
- Disabled / unknown provider
- Provider/model fields on LLMResult accuracy

No real network calls: `requests.post` / `requests.get` are monkeypatched
per-test.
"""

from __future__ import annotations

import importlib


def _reload_module(monkeypatch, env: dict[str, str]):
    """Reset all LLM-related env vars and reload the module so the new
    `LocalLLMClient()` reads the desired env."""
    for key in [
        "NONGTRI_LLM_ENABLED",
        "NONGTRI_LLM_PROVIDER",
        "NONGTRI_LLM_FALLBACK",
        "NONGTRI_LLM_MODEL",
        "NONGTRI_LLM_TIMEOUT_SECONDS",
        "NONGTRI_LLM_PRIMARY_TIMEOUT_SECONDS",
        "NONGTRI_OLLAMA_BASE_URL",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.ml_agri_chat.modules.llm_client as llm_client

    return importlib.reload(llm_client)


class _StubResponse:
    def __init__(self, *, status_code: int = 200, json_payload=None, text: str = "", ok: bool = True):
        self.status_code = status_code
        self._json = json_payload if json_payload is not None else {}
        self.text = text
        self.ok = ok

    def json(self):
        return self._json

    def raise_for_status(self):
        if not self.ok:
            import requests

            err = requests.HTTPError(f"HTTP {self.status_code}")
            err.response = self
            raise err


# ---------------- Default config (deepseek primary, ollama fallback) ----------------


def test_default_primary_is_deepseek_with_ollama_fallback(monkeypatch):
    mod = _reload_module(monkeypatch, {"DEEPSEEK_API_KEY": "sk-x"})
    client = mod.LocalLLMClient()
    assert client.provider == "deepseek"
    # Internal state: fallback wired up.
    assert client._fallback is not None
    assert client._fallback.name == "ollama"


def test_primary_unconfigured_promotes_fallback(monkeypatch):
    """DeepSeek primary with no key + Ollama fallback => Ollama becomes primary."""
    mod = _reload_module(monkeypatch, {})  # no DEEPSEEK_API_KEY
    client = mod.LocalLLMClient()
    assert client.provider == "ollama"
    # After promotion, fallback chain is gone (avoids loops).
    assert client._fallback is None


def test_explicit_disable_fallback(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": ""},
    )
    client = mod.LocalLLMClient()
    assert client.provider == "deepseek"
    assert client._fallback is None


# ---------------- Disabled / unknown ----------------


def test_disabled_when_env_off(monkeypatch):
    mod = _reload_module(monkeypatch, {"NONGTRI_LLM_ENABLED": "false"})
    client = mod.LocalLLMClient()
    assert client.is_enabled() is False
    result = client.generate("hello")
    assert result.text == ""
    assert result.used_fallback is True
    assert "disabled" in (result.error or "").lower()


def test_unknown_provider_no_fallback(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {
            "NONGTRI_LLM_PROVIDER": "anthropic",
            "NONGTRI_LLM_FALLBACK": "",
        },
    )
    client = mod.LocalLLMClient()
    assert client.is_enabled() is False
    assert "unsupported" in (client.generate("x").error or "").lower()


# ---------------- Ollama (single provider mode) ----------------


def test_ollama_generate_success(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {
            "NONGTRI_LLM_PROVIDER": "ollama",
            "NONGTRI_LLM_FALLBACK": "",
            "NONGTRI_LLM_MODEL": "qwen2.5:7b",
            "NONGTRI_OLLAMA_BASE_URL": "http://ollama.local:11434/",
        },
    )

    captured: dict = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _StubResponse(json_payload={"response": "  câu trả lời  "})

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate("xin chào", temperature=0.2)
    assert result.text == "câu trả lời"
    assert result.provider == "ollama"
    assert result.model == "qwen2.5:7b"
    assert result.used_fallback is False
    assert captured["url"] == "http://ollama.local:11434/api/generate"
    assert captured["json"]["options"]["temperature"] == 0.2


def test_ollama_status_unavailable(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"NONGTRI_LLM_PROVIDER": "ollama", "NONGTRI_LLM_FALLBACK": ""},
    )

    def fake_get(url, timeout):
        raise mod.requests.ConnectionError("boom")

    monkeypatch.setattr(mod.requests, "get", fake_get)

    status = mod.LocalLLMClient().status()
    assert status["primary"]["provider"] == "ollama"
    assert status["primary"]["available"] is False
    assert status["fallback"] is None


# ---------------- DeepSeek (single provider mode) ----------------


def test_deepseek_generate_success(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {
            "DEEPSEEK_API_KEY": "sk-test-123",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com/",
            "DEEPSEEK_MODEL": "deepseek-v4-flash",
            "NONGTRI_LLM_FALLBACK": "",  # isolate DeepSeek
        },
    )

    captured: dict = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _StubResponse(
            json_payload={
                "choices": [{"message": {"role": "assistant", "content": "hello world"}}]
            }
        )

    monkeypatch.setattr(mod.requests, "post", fake_post)

    client = mod.LocalLLMClient()
    assert client.provider == "deepseek"
    result = client.generate("ping", temperature=0.0)
    assert result.text == "hello world"
    assert result.used_fallback is False
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test-123"
    assert captured["json"]["messages"] == [{"role": "user", "content": "ping"}]
    assert result.provider == "deepseek"
    assert result.model == "deepseek-v4-flash"


def test_deepseek_http_error_no_fallback(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-bad", "NONGTRI_LLM_FALLBACK": ""},
    )

    def fake_post(url, headers, json, timeout):
        return _StubResponse(status_code=401, text='{"error":"invalid key"}', ok=False)

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate("ping")
    assert result.used_fallback is True
    assert "401" in (result.error or "")


def test_deepseek_missing_choices(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": ""},
    )

    def fake_post(url, headers, json, timeout):
        return _StubResponse(json_payload={"unexpected": "shape"})

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate("ping")
    assert result.used_fallback is True
    assert "choices" in (result.error or "").lower()


def test_deepseek_status_ok(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": ""},
    )

    def fake_get(url, headers, timeout):
        assert url == "https://api.deepseek.com/models"
        assert headers["Authorization"] == "Bearer sk-x"
        return _StubResponse(json_payload={"data": []})

    monkeypatch.setattr(mod.requests, "get", fake_get)

    status = mod.LocalLLMClient().status()
    assert status["primary"]["available"] is True
    assert status["fallback"] is None


# ---------------- Fallback chain ----------------


def test_fallback_fires_when_primary_runtime_fail(monkeypatch):
    """Primary DeepSeek configured but HTTP errors -> Ollama serves response."""
    mod = _reload_module(
        monkeypatch,
        {
            "DEEPSEEK_API_KEY": "sk-x",
            "NONGTRI_LLM_FALLBACK": "ollama",
            "NONGTRI_LLM_MODEL": "",  # let each provider use its own default
        },
    )

    def fake_post(url, **kwargs):
        if "deepseek.com" in url:
            return _StubResponse(status_code=502, text="bad gateway", ok=False)
        if "/api/generate" in url:  # Ollama
            return _StubResponse(json_payload={"response": "fallback answer"})
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(mod.requests, "post", fake_post)

    client = mod.LocalLLMClient()
    # Sanity: primary really is deepseek, fallback wired.
    assert client.provider == "deepseek"
    assert client._fallback is not None

    result = client.generate("ping")
    assert result.text == "fallback answer"
    assert result.provider == "ollama"
    assert result.model == "qwen2.5:3b"
    # Fallback served a real answer => used_fallback is False (no failure).
    assert result.used_fallback is False
    # Error string surfaces *why* we fell back, for ops debugging.
    assert "primary deepseek unavailable" in (result.error or "")
    assert "served by fallback ollama" in (result.error or "")
    # LLMResult.provider/model reflect the real source even when fallback
    # served the response.
    assert result.provider == "ollama"
    assert result.model == "qwen2.5:3b"


def test_fallback_both_fail_aggregates_error(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": "ollama"},
    )

    def fake_post(url, **kwargs):
        if "deepseek.com" in url:
            return _StubResponse(status_code=503, text="cloud down", ok=False)
        if "/api/generate" in url:
            raise mod.requests.ConnectionError("ollama refused")
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate("ping")
    assert result.used_fallback is True
    assert result.text == ""
    assert "primary deepseek failed" in (result.error or "")
    assert "fallback ollama failed" in (result.error or "")
    assert "503" in (result.error or "")
    assert "refused" in (result.error or "")
    # Provider/model strings show the chain so logs can grep by chain shape.
    assert result.provider == "deepseek->ollama"


def test_fallback_skipped_when_primary_succeeds(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": "ollama"},
    )

    calls: list[str] = []

    def fake_post(url, **kwargs):
        calls.append(url)
        if "deepseek.com" in url:
            return _StubResponse(
                json_payload={"choices": [{"message": {"content": "ok"}}]}
            )
        raise AssertionError(f"fallback should not be called, got {url}")

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate("ping")
    assert result.text == "ok"
    assert result.provider == "deepseek"
    assert all("deepseek.com" in url for url in calls)


def test_status_includes_both_when_fallback_configured(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": "ollama"},
    )

    def fake_get(url, **kwargs):
        if "deepseek.com" in url:
            return _StubResponse(json_payload={"data": []})
        if "/api/tags" in url:
            return _StubResponse(json_payload={"models": []})
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(mod.requests, "get", fake_get)

    status = mod.LocalLLMClient().status()
    assert status["primary"]["provider"] == "deepseek"
    assert status["primary"]["available"] is True
    assert status["fallback"]["provider"] == "ollama"
    assert status["fallback"]["available"] is True


def test_same_primary_and_fallback_skips_fallback(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {
            "NONGTRI_LLM_PROVIDER": "ollama",
            "NONGTRI_LLM_FALLBACK": "ollama",
        },
    )
    client = mod.LocalLLMClient()
    assert client.provider == "ollama"
    assert client._fallback is None


def test_deepseek_passes_response_format_to_api(monkeypatch):
    """When the caller asks for json_object, we must forward that to DeepSeek."""
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": ""},
    )

    captured: dict = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _StubResponse(
            json_payload={"choices": [{"message": {"content": '{"ok": true}'}}]}
        )

    monkeypatch.setattr(mod.requests, "post", fake_post)

    mod.LocalLLMClient().generate(
        "ping", temperature=0.0, response_format={"type": "json_object"}
    )
    assert captured["json"]["response_format"] == {"type": "json_object"}


def test_response_format_omitted_when_not_requested(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": ""},
    )

    captured: dict = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _StubResponse(
            json_payload={"choices": [{"message": {"content": "ok"}}]}
        )

    monkeypatch.setattr(mod.requests, "post", fake_post)

    mod.LocalLLMClient().generate("ping")
    assert "response_format" not in captured["json"]


def test_ollama_ignores_response_format(monkeypatch):
    """Ollama provider must accept the kwarg without crashing or forwarding."""
    mod = _reload_module(
        monkeypatch,
        {"NONGTRI_LLM_PROVIDER": "ollama", "NONGTRI_LLM_FALLBACK": ""},
    )

    captured: dict = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return _StubResponse(json_payload={"response": "ok"})

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate(
        "ping", response_format={"type": "json_object"}
    )
    assert result.used_fallback is False
    assert "response_format" not in captured["json"]


def test_deepseek_retries_on_5xx_and_succeeds(monkeypatch):
    """503 then 200 -> retry kicks in, returns the 200 text."""
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": ""},
    )
    monkeypatch.setattr(mod.time, "sleep", lambda *_a, **_kw: None)  # no real sleep

    calls = {"n": 0}

    def fake_post(url, headers, json, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return _StubResponse(status_code=503, text="busy", ok=False)
        return _StubResponse(
            json_payload={"choices": [{"message": {"content": "ok"}}]}
        )

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate("ping")
    assert result.used_fallback is False
    assert result.text == "ok"
    assert calls["n"] == 2  # one retry


def test_deepseek_retries_exhausted_returns_fallback(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": ""},
    )
    monkeypatch.setattr(mod.time, "sleep", lambda *_a, **_kw: None)

    def fake_post(url, headers, json, timeout):
        return _StubResponse(status_code=503, text="busy", ok=False)

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate("ping")
    assert result.used_fallback is True
    # Final attempt's raise_for_status() lands in HTTPError handler -> we
    # return the 503 string, not "retries exhausted".
    assert "503" in (result.error or "")


def test_deepseek_4xx_not_retried(monkeypatch):
    """A 401 must terminate immediately - retrying does not fix auth."""
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-bad", "NONGTRI_LLM_FALLBACK": ""},
    )
    monkeypatch.setattr(mod.time, "sleep", lambda *_a, **_kw: None)

    calls = {"n": 0}

    def fake_post(url, headers, json, timeout):
        calls["n"] += 1
        return _StubResponse(status_code=401, text="invalid key", ok=False)

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate("ping")
    assert result.used_fallback is True
    assert calls["n"] == 1


def test_deepseek_timeout_retries_then_yields(monkeypatch):
    mod = _reload_module(
        monkeypatch,
        {"DEEPSEEK_API_KEY": "sk-x", "NONGTRI_LLM_FALLBACK": ""},
    )
    monkeypatch.setattr(mod.time, "sleep", lambda *_a, **_kw: None)

    calls = {"n": 0}

    def fake_post(url, headers, json, timeout):
        calls["n"] += 1
        raise mod.requests.Timeout("slow")

    monkeypatch.setattr(mod.requests, "post", fake_post)

    result = mod.LocalLLMClient().generate("ping")
    assert result.used_fallback is True
    assert calls["n"] == 3  # initial + 2 retries
    assert "exhausted" in (result.error or "")
