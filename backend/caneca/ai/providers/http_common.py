"""Shared HTTP plumbing: error mapping and streaming line readers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

import httpx

from caneca.ai.providers.base import ProviderError

MAX_LINE_BYTES = 1_000_000


def validate_base_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ProviderError("bad_request", "URL inválida: use http:// ou https://")
    return url.rstrip("/")


def map_http_error(exc: Exception) -> ProviderError:
    if isinstance(exc, ProviderError):
        return exc
    if isinstance(exc, httpx.TimeoutException):
        return ProviderError("timeout", "o modelo demorou demais para responder")
    if isinstance(exc, httpx.ConnectError | httpx.NetworkError):
        return ProviderError("unavailable", "não foi possível conectar ao serviço de IA")
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return ProviderError("auth", "credencial recusada pelo provedor")
        if status == 404:
            return ProviderError("model_missing", "modelo não encontrado no provedor")
        if status == 429:
            return ProviderError("rate_limited", "limite de requisições do provedor atingido")
        if 400 <= status < 500:
            return ProviderError("bad_request", f"requisição recusada ({status})")
        return ProviderError("unavailable", f"o provedor respondeu com erro {status}")
    return ProviderError("invalid_response", str(exc) or exc.__class__.__name__)


async def raise_for_status(response: httpx.Response) -> None:
    if response.status_code >= 400:
        await response.aread()
        response.raise_for_status()


async def iter_json_lines(response: httpx.Response) -> AsyncIterator[dict[str, Any]]:
    """NDJSON stream (Ollama)."""
    async for line in response.aiter_lines():
        if not line.strip():
            continue
        if len(line) > MAX_LINE_BYTES:
            raise ProviderError("invalid_response", "linha de streaming grande demais")
        try:
            yield json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProviderError("invalid_response", "resposta de streaming inválida") from exc


async def iter_sse(response: httpx.Response) -> AsyncIterator[tuple[str, str]]:
    """Server-sent events stream (OpenAI-compatible and Anthropic). Yields (event, data)."""
    event = "message"
    data_lines: list[str] = []
    async for line in response.aiter_lines():
        if len(line) > MAX_LINE_BYTES:
            raise ProviderError("invalid_response", "evento de streaming grande demais")
        if line == "":
            if data_lines:
                yield event, "\n".join(data_lines)
            event, data_lines = "message", []
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value
        if field == "event":
            event = value
        elif field == "data":
            data_lines.append(value)
    if data_lines:
        yield event, "\n".join(data_lines)
