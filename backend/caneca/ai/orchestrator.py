"""Runs the model calls of a turn: intent refinement, narration streaming, summaries.

Failures never touch the saved game: the engine result is committed before narration
starts, and the deterministic text is always available as a fallback.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

import anyio

from caneca.ai.config import AISettings
from caneca.ai.prompts import (
    NarrationPrompt,
    build_intent_prompt,
    build_summary_prompt,
    intent_schema,
)
from caneca.ai.providers.base import ChatMessage, GenerationParams, Provider, ProviderError, Usage
from caneca.ai.safety import ThinkFilter, acceptable, clean_narration
from caneca.game.engine import Engine
from caneca.game.i18n import tr
from caneca.game.parser import Intent
from caneca.game.state import WorldState

log = logging.getLogger(__name__)

INTENT_TIMEOUT = 25.0
MAX_STREAM_CHARS = 6000


@dataclass
class NarrationResult:
    text: str
    source: str  # "ai" | "fallback" | "cancelled"
    usage: Usage
    error: ProviderError | None = None


class Narrator:
    def __init__(self, provider: Provider, ai: AISettings, provider_id: str) -> None:
        self.provider = provider
        self.ai = ai
        self.provider_id = provider_id
        self.model = ai.model_for(provider_id)

    def _params(
        self,
        max_tokens: int,
        schema: dict[str, object] | None = None,
        timeout: float | None = None,
        temperature: float | None = None,
    ) -> GenerationParams:
        return GenerationParams(
            model=self.model,
            temperature=self.ai.temperature if temperature is None else temperature,
            max_tokens=max_tokens,
            context_tokens=self.ai.context_tokens,
            timeout=float(timeout or self.ai.timeout_seconds),
            json_schema=schema,
        )

    async def stream_narration(
        self,
        prompt: NarrationPrompt,
        fallback: str,
        cancel: anyio.Event,
        sink: list[str],
    ) -> AsyncIterator[str]:
        """Yields cleaned deltas; appends the full raw text to ``sink`` as it goes."""
        messages = [ChatMessage("system", prompt.system), ChatMessage("user", prompt.user)]
        usage = Usage()
        self.last_usage = usage
        think = ThinkFilter()
        total = 0
        async for chunk in self.provider.stream(messages, self._params(prompt.max_tokens), usage):
            if cancel.is_set():
                return
            visible = think.feed(chunk)
            if visible:
                total += len(visible)
                if total > MAX_STREAM_CHARS:
                    return
                sink.append(visible)
                yield visible
        rest = think.flush()
        if rest:
            sink.append(rest)
            yield rest

    def finalize(self, raw: str, fallback: str, max_tokens: int) -> tuple[str, bool]:
        text = clean_narration(raw, max_chars=max_tokens * 6)
        if acceptable(text):
            return text, True
        return fallback, False

    async def refine_intent(self, engine: Engine, state: WorldState, text: str, parsed: Intent) -> Intent:
        lang = state.settings.language
        cands = engine.candidates(state)
        pairs: list[tuple[str, str]] = []
        for c in cands:
            if c.kind == "self":
                pairs.append(("self", "self / myself / my body"))
            else:
                name = c.keywords[-2:] if len(c.keywords) >= 2 else c.keywords
                pairs.append((c.id, " / ".join(dict.fromkeys(name))))
        system, user = build_intent_prompt(text, pairs)
        usage = Usage()
        try:
            with anyio.fail_after(INTENT_TIMEOUT):
                raw = await self.provider.complete(
                    [ChatMessage("system", system), ChatMessage("user", user)],
                    self._params(
                        120, intent_schema([p[0] for p in pairs]), timeout=INTENT_TIMEOUT, temperature=0.0
                    ),
                    usage,
                )
        except (ProviderError, TimeoutError) as exc:
            log.info("intent refinement skipped: %s", exc)
            return parsed
        data = _extract_json(raw)
        if data is None:
            return parsed
        ids = {p[0] for p in pairs}
        verb, target, item = data.get("verb"), data.get("target"), data.get("item")
        if target is not None and target not in ids:
            return parsed
        if item is not None and item not in ids:
            return parsed
        try:
            refined = Intent(verb=verb, target=target, item=item, raw=parsed.raw, source="ai", confidence=0.7)
        except ValueError:
            return parsed
        if refined.verb in ("inventory", "status", "help"):
            return parsed
        _ = lang
        return refined

    async def summarize(self, lang: str, previous: str, entries: list[str]) -> str | None:
        system, user = build_summary_prompt(lang, previous, entries)
        try:
            with anyio.fail_after(self.ai.timeout_seconds):
                raw = await self.provider.complete(
                    [ChatMessage("system", system), ChatMessage("user", user)],
                    self._params(260, temperature=0.3),
                    Usage(),
                )
        except (ProviderError, TimeoutError) as exc:
            log.info("summary skipped: %s", exc)
            return None
        text = clean_narration(raw, 1200)
        return text if acceptable(text) else None


def _extract_json(raw: str) -> dict[str, object] | None:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def offline_summary(lang: str, previous: str, entries: list[str], limit: int = 1500) -> str:
    """Deterministic summary used without AI: newest important lines win."""
    combined = (previous + " " + " ".join(entries)).strip()
    if len(combined) <= limit:
        return combined
    return "…" + combined[-limit:]


def journal_line(entry_title: dict[str, str], body: dict[str, str], lang: str) -> str:
    return f"{tr(entry_title, lang)}: {tr(body, lang)}"
