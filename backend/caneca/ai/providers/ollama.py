"""Ollama adapter (local models). API reference: https://github.com/ollama/ollama/blob/main/docs/api.md"""

from __future__ import annotations

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
    iter_json_lines,
    map_http_error,
    raise_for_status,
    validate_base_url,
)


class OllamaProvider:
    id = "ollama"

    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = validate_base_url(base_url)
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=5.0),
            transport=self._transport,
        )

    async def status(self) -> ProviderStatus:
        try:
            async with self._client(8.0) as client:
                version = await client.get("/api/version")
                await raise_for_status(version)
                tags = await client.get("/api/tags")
                await raise_for_status(tags)
        except Exception as exc:
            err = map_http_error(exc)
            return ProviderStatus(False, err.message)
        models = [
            ModelInfo(
                id=m.get("model") or m["name"],
                name=m.get("name") or m.get("model", ""),
                size_bytes=m.get("size"),
                details=m.get("details") or {},
            )
            for m in tags.json().get("models", [])
            if m.get("name") or m.get("model")
        ]
        detail = f"Ollama {version.json().get('version', '?')}"
        return ProviderStatus(True, detail, models)

    def _payload(self, messages: list[ChatMessage], params: GenerationParams) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": params.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "keep_alive": "15m",
            "options": {
                "temperature": params.temperature,
                "num_ctx": params.context_tokens,
                "num_predict": params.max_tokens,
                "top_p": params.top_p,
            },
        }
        if params.json_schema is not None:
            payload["format"] = params.json_schema
        return payload

    async def stream(
        self, messages: list[ChatMessage], params: GenerationParams, usage: Usage
    ) -> AsyncIterator[str]:
        if not params.model:
            raise ProviderError("model_missing", "nenhum modelo selecionado")
        try:
            async with (
                self._client(params.timeout) as client,
                client.stream("POST", "/api/chat", json=self._payload(messages, params)) as response,
            ):
                await raise_for_status(response)
                async for chunk in iter_json_lines(response):
                    if "error" in chunk:
                        raise ProviderError("invalid_response", str(chunk["error"])[:200])
                    text = (chunk.get("message") or {}).get("content") or ""
                    if text:
                        yield text
                    if chunk.get("done"):
                        usage.tokens_in += int(chunk.get("prompt_eval_count") or 0)
                        usage.tokens_out += int(chunk.get("eval_count") or 0)
                        return
        except ProviderError:
            raise
        except Exception as exc:
            raise map_http_error(exc) from exc

    async def complete(self, messages: list[ChatMessage], params: GenerationParams, usage: Usage) -> str:
        return await collect(self, messages, params, usage)
