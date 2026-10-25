"""Cloud adapters: any OpenAI-compatible Chat Completions API, and Anthropic Messages.

Keys are held only by the backend (env vars or the 0600 secrets file); they are never
sent to the browser.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from caneca.ai.providers.base import (
    ChatMessage,
    GenerationParams,
    ModelInfo,
    ProviderError,
    ProviderStatus,
    Usage,
    collect,
)
from caneca.ai.providers.http_common import (
    iter_sse,
    map_http_error,
    raise_for_status,
    validate_base_url,
)


class OpenAICompatibleProvider:
    """OpenAI, OpenRouter, Groq, LM Studio, vLLM, llama.cpp server..."""

    id = "openai"

    def __init__(
        self, base_url: str, api_key: str | None, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.base_url = validate_base_url(base_url)
        self.api_key = api_key
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout, connect=8.0),
            transport=self._transport,
        )

    async def status(self) -> ProviderStatus:
        try:
            async with self._client(10.0) as client:
                resp = await client.get("/models")
                await raise_for_status(resp)
        except Exception as exc:
            return ProviderStatus(False, map_http_error(exc).message)
        data = resp.json().get("data", [])
        models = [ModelInfo(id=m["id"], name=m["id"]) for m in data if isinstance(m, dict) and "id" in m]
        return ProviderStatus(True, f"{len(models)} modelos", sorted(models, key=lambda m: m.id))

    async def stream(
        self, messages: list[ChatMessage], params: GenerationParams, usage: Usage
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": params.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": params.temperature,
            "top_p": params.top_p,
            "max_tokens": params.max_tokens,
        }
        if params.json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "intent", "schema": params.json_schema, "strict": True},
            }
        try:
            async with (
                self._client(params.timeout) as client,
                client.stream("POST", "/chat/completions", json=payload) as response,
            ):
                await raise_for_status(response)
                async for _event, data in iter_sse(response):
                    if data.strip() == "[DONE]":
                        return
                    chunk = _loads(data)
                    if chunk.get("usage"):
                        usage.tokens_in += int(chunk["usage"].get("prompt_tokens") or 0)
                        usage.tokens_out += int(chunk["usage"].get("completion_tokens") or 0)
                    for choice in chunk.get("choices") or []:
                        text = (choice.get("delta") or {}).get("content") or ""
                        if text:
                            yield text
        except ProviderError:
            raise
        except Exception as exc:
            raise map_http_error(exc) from exc

    async def complete(self, messages: list[ChatMessage], params: GenerationParams, usage: Usage) -> str:
        return await collect(self, messages, params, usage)


class AnthropicProvider:
    id = "anthropic"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: str | None,
        base_url: str = "https://api.anthropic.com",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = validate_base_url(base_url)
        self.api_key = api_key
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        headers = {"anthropic-version": self.API_VERSION, "content-type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout, connect=8.0),
            transport=self._transport,
        )

    async def status(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus(False, "chave de API não configurada")
        try:
            async with self._client(10.0) as client:
                resp = await client.get("/v1/models", params={"limit": 100})
                await raise_for_status(resp)
        except Exception as exc:
            return ProviderStatus(False, map_http_error(exc).message)
        models = [
            ModelInfo(id=m["id"], name=m.get("display_name") or m["id"])
            for m in resp.json().get("data", [])
            if "id" in m
        ]
        return ProviderStatus(True, f"{len(models)} modelos", models)

    async def stream(
        self, messages: list[ChatMessage], params: GenerationParams, usage: Usage
    ) -> AsyncIterator[str]:
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        convo = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        payload: dict[str, Any] = {
            "model": params.model,
            "max_tokens": params.max_tokens,
            "temperature": min(params.temperature, 1.0),
            "system": system,
            "messages": convo,
            "stream": True,
        }
        try:
            async with (
                self._client(params.timeout) as client,
                client.stream("POST", "/v1/messages", json=payload) as response,
            ):
                await raise_for_status(response)
                async for event, data in iter_sse(response):
                    chunk = _loads(data)
                    if event == "error":
                        message = (chunk.get("error") or {}).get("message", "erro do provedor")
                        raise ProviderError("unavailable", str(message)[:200])
                    if event == "message_start":
                        u = (chunk.get("message") or {}).get("usage") or {}
                        usage.tokens_in += int(u.get("input_tokens") or 0)
                    elif event == "content_block_delta":
                        delta = chunk.get("delta") or {}
                        if delta.get("type") == "text_delta" and delta.get("text"):
                            yield delta["text"]
                    elif event == "message_delta":
                        u = chunk.get("usage") or {}
                        usage.tokens_out += int(u.get("output_tokens") or 0)
                    elif event == "message_stop":
                        return
        except ProviderError:
            raise
        except Exception as exc:
            raise map_http_error(exc) from exc

    async def complete(self, messages: list[ChatMessage], params: GenerationParams, usage: Usage) -> str:
        return await collect(self, messages, params, usage)


def _loads(data: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ProviderError("invalid_response", "evento de streaming inválido") from exc
    if not isinstance(value, dict):
        raise ProviderError("invalid_response", "evento de streaming inesperado")
    return value
