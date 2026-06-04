from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    used_fallback: bool = False
    error: str | None = None


class LocalLLMClient:
    """Small Ollama-compatible client with a deterministic off switch."""

    def __init__(self) -> None:
        self.provider = os.getenv("NONGTRI_LLM_PROVIDER", "ollama").strip().lower()
        self.model = os.getenv("NONGTRI_LLM_MODEL", "qwen2.5:3b").strip()
        self.base_url = os.getenv("NONGTRI_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.timeout_seconds = float(os.getenv("NONGTRI_LLM_TIMEOUT_SECONDS", "35"))
        self.enabled = os.getenv("NONGTRI_LLM_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}

    def is_enabled(self) -> bool:
        return self.enabled and self.provider == "ollama"

    def generate(self, prompt: str, *, temperature: float = 0.1) -> LLMResult:
        if not self.is_enabled():
            return LLMResult(
                text="",
                provider=self.provider,
                model=self.model,
                used_fallback=True,
                error="LLM is disabled or provider is unsupported.",
            )

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
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            return LLMResult(text=(payload.get("response") or "").strip(), provider=self.provider, model=self.model)
        except Exception as exc:
            return LLMResult(
                text="",
                provider=self.provider,
                model=self.model,
                used_fallback=True,
                error=str(exc),
            )

    def status(self) -> dict[str, Any]:
        status = {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "available": False,
        }
        if not self.is_enabled():
            return status
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            status["available"] = response.ok
        except Exception:
            status["available"] = False
        return status
