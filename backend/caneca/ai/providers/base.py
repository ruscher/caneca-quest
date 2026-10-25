"""Provider-agnostic contracts for language model backends."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass
class GenerationParams:
    model: str
    temperature: float = 0.8
    max_tokens: int = 400
    context_tokens: int = 4096
    top_p: float = 0.95
    timeout: float = 90.0
    json_schema: dict[str, Any] | None = None


@dataclass
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class ModelInfo:
    id: str
    name: str
    size_bytes: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderStatus:
    available: bool
    detail: str = ""
    models: list[ModelInfo] = field(default_factory=list)


ErrorCode = Literal[
    "unavailable",
    "timeout",
    "auth",
    "rate_limited",
    "model_missing",
    "invalid_response",
    "bad_request",
    "cancelled",
]


class ProviderError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Provider(Protocol):
    id: str

    async def status(self) -> ProviderStatus: ...

    def stream(
        self, messages: list[ChatMessage], params: GenerationParams, usage: Usage
    ) -> AsyncIterator[str]: ...

    async def complete(self, messages: list[ChatMessage], params: GenerationParams, usage: Usage) -> str: ...


async def collect(
    provider: Provider, messages: list[ChatMessage], params: GenerationParams, usage: Usage
) -> str:
    """Helper for providers whose ``complete`` is just a drained stream."""
    parts: list[str] = []
    async for chunk in provider.stream(messages, params, usage):
        parts.append(chunk)
    return "".join(parts)
