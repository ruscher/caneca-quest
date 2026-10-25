"""AI settings (stored in the database) and API keys (stored outside it, never exposed)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import ClassVar, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from caneca.ai.providers.base import Provider, ProviderError
from caneca.ai.providers.cloud import AnthropicProvider, OpenAICompatibleProvider
from caneca.ai.providers.http_common import validate_base_url
from caneca.ai.providers.ollama import OllamaProvider
from caneca.config import Settings

ProviderId = Literal["offline", "ollama", "openai", "anthropic"]
CLOUD_PROVIDERS: tuple[str, ...] = ("openai", "anthropic")


class AISettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderId = "offline"
    models: dict[str, str] = Field(default_factory=dict)
    ollama_url: str = "http://127.0.0.1:11434"
    openai_base_url: str = "https://api.openai.com/v1"
    temperature: float = Field(default=0.8, ge=0.0, le=1.5)
    context_tokens: int = Field(default=4096, ge=1024, le=131072)
    timeout_seconds: int = Field(default=90, ge=10, le=600)
    ai_intent: bool = True
    memory_turns: int = Field(default=4, ge=0, le=12)
    summary_every: int = Field(default=12, ge=4, le=60)
    cloud_consent: bool = False

    @field_validator("ollama_url", "openai_base_url")
    @classmethod
    def _url(cls, value: str) -> str:
        try:
            return validate_base_url(value)
        except ProviderError as exc:
            raise ValueError(exc.message) from exc

    @field_validator("models")
    @classmethod
    def _models(cls, value: dict[str, str]) -> dict[str, str]:
        for key, model in value.items():
            if key not in ("ollama", "openai", "anthropic") or len(model) > 200:
                raise ValueError("modelo inválido")
        return value

    def model_for(self, provider: str) -> str:
        return self.models.get(provider, "")


class SecretStore:
    """API keys: environment variables win; otherwise a 0600 JSON file in the data dir."""

    ENV: ClassVar[dict[str, str]] = {
        "openai": "CANECA_OPENAI_API_KEY",
        "anthropic": "CANECA_ANTHROPIC_API_KEY",
    }

    def __init__(self, path: Path) -> None:
        self.path = path

    def _read(self) -> dict[str, str]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError):
            return {}
        return {k: v for k, v in data.items() if isinstance(v, str)}

    def get(self, provider: str) -> str | None:
        env = self.ENV.get(provider)
        if env and os.environ.get(env):
            return os.environ[env]
        return self._read().get(provider) or None

    def source(self, provider: str) -> str | None:
        env = self.ENV.get(provider)
        if env and os.environ.get(env):
            return "env"
        return "file" if self._read().get(provider) else None

    def set(self, provider: str, key: str | None) -> None:
        data = self._read()
        if key:
            data[provider] = key
        else:
            data.pop(provider, None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(tmp, self.path)
        os.chmod(self.path, 0o600)


def build_provider(
    provider: str,
    ai: AISettings,
    secrets: SecretStore,
    settings: Settings,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Provider | None:
    if provider == "ollama":
        return OllamaProvider(ai.ollama_url, transport)
    if provider == "openai":
        return OpenAICompatibleProvider(ai.openai_base_url, secrets.get("openai"), transport)
    if provider == "anthropic":
        return AnthropicProvider(secrets.get("anthropic"), transport=transport)
    return None
