"""LLM client facade with pluggable providers + automatic fallback.

Provider selection (env-driven):

- `NONGTRI_LLM_PROVIDER` (default `deepseek`): primary provider.
- `NONGTRI_LLM_FALLBACK` (default `ollama`): provider used when the primary
  is unconfigured or fails at runtime. Set to an empty string to disable
  fallback entirely.

Supported provider names:

- `deepseek`: DeepSeek's OpenAI-compatible `/chat/completions` endpoint.
  Docs: https://api-docs.deepseek.com/.
- `ollama`: local Ollama daemon's `/api/generate` endpoint.

The public surface (`LocalLLMClient`, `LLMResult`) is preserved so existing
callers (`llm_advisor.ControlledAdvisor`, `router.health`) keep working.
After every `generate()` call, `LocalLLMClient.last_call_provider` /
`last_call_model` reflect *which* provider actually served the response, so
diagnostic blocks downstream can log the truth (not the configured primary).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests


# Default Ollama model. The env var `NONGTRI_LLM_MODEL` overrides this.
_DEFAULT_OLLAMA_MODEL = "qwen2.5:3b"

# DeepSeek defaults. `deepseek-v4-flash` is the non-thinking model (fast,
# cheap). Use `deepseek-v4-pro` for thinking mode. The older `deepseek-chat`
# / `deepseek-reasoner` aliases will be deprecated by DeepSeek on
# 2026-07-24.
_DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"

# Defaults
_DEFAULT_PRIMARY = "deepseek"
_DEFAULT_FALLBACK = "ollama"
# Primary times out faster than fallback so the user does not wait the full
# 35s when the cloud call is stuck.
_DEFAULT_PRIMARY_TIMEOUT = 15.0
_DEFAULT_FALLBACK_TIMEOUT = 35.0


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    used_fallback: bool = False
    error: str | None = None


class _Provider(ABC):
    """Internal provider interface. Not part of the public API."""

    name: str
    model: str

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        temperature: float,
        timeout_override: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResult: ...

    @abstractmethod
    def status(self) -> dict[str, Any]: ...

    def is_configured(self) -> bool:
        """Return False if the provider obviously cannot serve traffic.

        Used at construction time to decide whether to promote the fallback
        to primary (e.g. DeepSeek primary with no API key configured).
        """
        return True


class _DisabledProvider(_Provider):
    """Marker for a provider that is off or unrecognised."""

    def __init__(self, name: str, model: str, reason: str) -> None:
        self.name = name
        self.model = model
        self._reason = reason

    def is_configured(self) -> bool:
        return False

    def generate(
        self,
        prompt: str,
        *,
        temperature: float,
        timeout_override: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResult:
        return LLMResult(
            text="",
            provider=self.name,
            model=self.model,
            used_fallback=True,
            error=self._reason,
        )

    def status(self) -> dict[str, Any]:
        return {
            "enabled": False,
            "provider": self.name,
            "model": self.model,
            "available": False,
            "error": self._reason,
        }


class _OllamaProvider(_Provider):
    """Talks to a local (or remote) Ollama daemon via `/api/generate`."""

    name = "ollama"

    def __init__(self, model: str, base_url: str, timeout_seconds: float) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        prompt: str,
        *,
        temperature: float,
        timeout_override: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResult:
        # Ollama does not advertise OpenAI-compatible response_format on the
        # /api/generate endpoint; the kwarg is accepted but ignored so the
        # facade signature stays uniform across providers.
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": 700,
                    },
                },
                timeout=timeout_override if timeout_override is not None else self.timeout_seconds,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            return LLMResult(
                text=(payload.get("response") or "").strip(),
                provider=self.name,
                model=self.model,
            )
        except Exception as exc:
            return LLMResult(
                text="",
                provider=self.name,
                model=self.model,
                used_fallback=True,
                error=str(exc),
            )

    def status(self) -> dict[str, Any]:
        status: dict[str, Any] = {
            "enabled": True,
            "provider": self.name,
            "model": self.model,
            "base_url": self.base_url,
            "available": False,
        }
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            status["available"] = response.ok
        except Exception as exc:
            status["available"] = False
            status["error"] = str(exc)
        return status


class _DeepSeekProvider(_Provider):
    """DeepSeek REST client (OpenAI-compatible chat completions)."""

    name = "deepseek"

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def generate(
        self,
        prompt: str,
        *,
        temperature: float,
        timeout_override: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResult:
        if not self._api_key:
            return LLMResult(
                text="",
                provider=self.name,
                model=self.model,
                used_fallback=True,
                error="DEEPSEEK_API_KEY is not set.",
            )
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 700,
            "stream": False,
        }
        if response_format is not None:
            # OpenAI-compatible: {"type": "json_object"} forces the model
            # to emit a single valid JSON object. Verified against
            # https://api-docs.deepseek.com (chat/completions schema).
            body["response_format"] = response_format
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
                timeout=timeout_override if timeout_override is not None else self.timeout_seconds,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            choices = payload.get("choices") or []
            if not choices:
                return LLMResult(
                    text="",
                    provider=self.name,
                    model=self.model,
                    used_fallback=True,
                    error="DeepSeek response missing `choices`.",
                )
            message = (choices[0] or {}).get("message") or {}
            text = (message.get("content") or "").strip()
            return LLMResult(text=text, provider=self.name, model=self.model)
        except requests.HTTPError as exc:
            body_snippet = ""
            if exc.response is not None:
                body_snippet = exc.response.text[:200]
            return LLMResult(
                text="",
                provider=self.name,
                model=self.model,
                used_fallback=True,
                error=f"HTTP {exc.response.status_code if exc.response else '?'}: {body_snippet}".strip(),
            )
        except Exception as exc:
            return LLMResult(
                text="",
                provider=self.name,
                model=self.model,
                used_fallback=True,
                error=str(exc),
            )

    def status(self) -> dict[str, Any]:
        status: dict[str, Any] = {
            "enabled": True,
            "provider": self.name,
            "model": self.model,
            "base_url": self.base_url,
            "available": False,
        }
        if not self._api_key:
            status["error"] = "DEEPSEEK_API_KEY is not set."
            return status
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=3,
            )
            status["available"] = response.ok
            if not response.ok:
                status["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception as exc:
            status["available"] = False
            status["error"] = str(exc)
        return status


def _build_provider_by_name(name: str, *, timeout_seconds: float) -> _Provider:
    """Construct a provider from a short name. Empty name -> _DisabledProvider."""
    name = (name or "").strip().lower()
    if not name:
        return _DisabledProvider("", "", "Provider name is empty.")

    if name == "ollama":
        return _OllamaProvider(
            model=os.getenv("NONGTRI_LLM_MODEL", _DEFAULT_OLLAMA_MODEL).strip()
            or _DEFAULT_OLLAMA_MODEL,
            base_url=os.getenv("NONGTRI_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            timeout_seconds=timeout_seconds,
        )

    if name == "deepseek":
        model = (
            os.getenv("NONGTRI_LLM_MODEL")
            or os.getenv("DEEPSEEK_MODEL")
            or _DEFAULT_DEEPSEEK_MODEL
        ).strip()
        return _DeepSeekProvider(
            model=model,
            base_url=os.getenv("DEEPSEEK_BASE_URL", _DEFAULT_DEEPSEEK_BASE_URL),
            api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            timeout_seconds=timeout_seconds,
        )

    return _DisabledProvider(name, "", f"Unsupported LLM provider: {name!r}.")


class LocalLLMClient:
    """Primary + optional fallback LLM client.

    By default the primary is DeepSeek (cloud) and Ollama (local) acts as a
    fallback when DeepSeek is unconfigured or fails at runtime. Behavior is
    controlled by env vars; see module docstring.

    Public attributes preserved for backward compatibility:
    - `provider`, `model`, `enabled`, `is_enabled()`
    - `generate(prompt, *, temperature)`
    - `status()` (shape changed: now returns `{primary, fallback}`)

    Added:
    - `last_call_provider`, `last_call_model`: the provider that actually
      served the most recent `generate()` call. Defaults to the primary
      until the first call.
    """

    def __init__(self) -> None:
        enabled = os.getenv("NONGTRI_LLM_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        primary_name = os.getenv("NONGTRI_LLM_PROVIDER", _DEFAULT_PRIMARY).strip().lower()
        # Empty string explicitly disables the fallback chain.
        fallback_name = os.getenv("NONGTRI_LLM_FALLBACK", _DEFAULT_FALLBACK).strip().lower()

        primary_timeout = float(
            os.getenv(
                "NONGTRI_LLM_PRIMARY_TIMEOUT_SECONDS",
                str(_DEFAULT_PRIMARY_TIMEOUT),
            )
        )
        fallback_timeout = float(
            os.getenv("NONGTRI_LLM_TIMEOUT_SECONDS", str(_DEFAULT_FALLBACK_TIMEOUT))
        )

        if not enabled:
            self._primary: _Provider = _DisabledProvider(
                primary_name, "", "LLM is disabled."
            )
            self._fallback: _Provider | None = None
        else:
            self._primary = _build_provider_by_name(
                primary_name, timeout_seconds=primary_timeout
            )
            # Skip building the fallback when:
            # - disabled by env (empty string)
            # - same provider as primary (no point)
            if fallback_name and fallback_name != primary_name:
                self._fallback = _build_provider_by_name(
                    fallback_name, timeout_seconds=fallback_timeout
                )
            else:
                self._fallback = None

            # Promote the fallback to primary when the configured primary is
            # not usable at construct time (e.g. DeepSeek with no key). This
            # avoids burning a round-trip on every request just to discover
            # missing config.
            if (
                not self._primary.is_configured()
                and self._fallback is not None
                and self._fallback.is_configured()
            ):
                self._primary, self._fallback = self._fallback, None

        self.enabled = enabled and not isinstance(self._primary, _DisabledProvider)
        # Static attrs reflect the primary (configured) provider.
        self.provider = self._primary.name
        self.model = self._primary.model
        self.base_url = getattr(self._primary, "base_url", "")
        # Mutable attrs reflecting the most recent generate() call.
        self.last_call_provider = self.provider
        self.last_call_model = self.model

    def is_enabled(self) -> bool:
        return self.enabled

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        timeout_override: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResult:
        result = self._primary.generate(
            prompt,
            temperature=temperature,
            timeout_override=timeout_override,
            response_format=response_format,
        )
        if not result.used_fallback or self._fallback is None:
            self.last_call_provider = result.provider
            self.last_call_model = result.model
            return result

        # Primary failed at runtime. Try fallback.
        primary_error = result.error or "unknown error"
        fallback_result = self._fallback.generate(
            prompt,
            temperature=temperature,
            timeout_override=timeout_override,
            response_format=response_format,
        )
        if fallback_result.used_fallback:
            # Both failed. Report aggregated error; keep primary-shaped
            # provider/model so logs still show the intended chain.
            self.last_call_provider = (
                f"{self._primary.name}->{self._fallback.name}"
            )
            self.last_call_model = (
                f"{self._primary.model}|{self._fallback.model}"
            )
            return LLMResult(
                text="",
                provider=self.last_call_provider,
                model=self.last_call_model,
                used_fallback=True,
                error=(
                    f"primary {self._primary.name} failed: {primary_error}; "
                    f"fallback {self._fallback.name} failed: "
                    f"{fallback_result.error or 'unknown error'}"
                ),
            )

        # Fallback served the response. Surface that explicitly so callers
        # log the truthful provider/model.
        self.last_call_provider = fallback_result.provider
        self.last_call_model = fallback_result.model
        return LLMResult(
            text=fallback_result.text,
            provider=fallback_result.provider,
            model=fallback_result.model,
            used_fallback=False,
            error=(
                f"primary {self._primary.name} unavailable "
                f"({primary_error}); served by fallback {self._fallback.name}."
            ),
        )

    def status(self) -> dict[str, Any]:
        return {
            "primary": self._primary.status(),
            "fallback": self._fallback.status() if self._fallback else None,
        }
