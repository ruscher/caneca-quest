"""Treat model output as untrusted data: filter, clean and validate it."""

from __future__ import annotations

import re

_REFUSAL_OR_LEAK = re.compile(
    r"(as an ai|como (uma )?ia\b|modelo de linguagem|language model|system prompt|"
    r"prompt do sistema|i cannot assist|não posso ajudar|regras invioláveis|unbreakable rules|"
    r"resultado oficial|official result)",
    re.IGNORECASE,
)
_MARKDOWN_LINE = re.compile(r"^\s*(#{1,6}\s+|[-*•]\s+|\d+[.)]\s+|>\s+)")
_CHOICES_TAIL = re.compile(
    r"\n\s*(o que (você )?(deseja|quer|vai) fazer\??|what (do|will) you do\??|opções:|options:).*$",
    re.IGNORECASE | re.DOTALL,
)


class ThinkFilter:
    """Removes <think>…</think> blocks from a token stream, across chunk boundaries."""

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self.buffer = ""
        self.inside = False

    def feed(self, chunk: str) -> str:
        self.buffer += chunk
        out: list[str] = []
        while self.buffer:
            if self.inside:
                end = self.buffer.find(self.CLOSE)
                if end == -1:
                    keep = len(self.CLOSE) - 1
                    self.buffer = self.buffer[-keep:]
                    break
                self.buffer = self.buffer[end + len(self.CLOSE) :]
                self.inside = False
            else:
                start = self.buffer.find(self.OPEN)
                if start == -1:
                    # Hold back a possible partial "<think" at the end.
                    safe = len(self.buffer)
                    for k in range(1, len(self.OPEN)):
                        if self.buffer.endswith(self.OPEN[:k]):
                            safe = len(self.buffer) - k
                            break
                    out.append(self.buffer[:safe])
                    self.buffer = self.buffer[safe:]
                    break
                out.append(self.buffer[:start])
                self.buffer = self.buffer[start + len(self.OPEN) :]
                self.inside = True
        return "".join(out)

    def flush(self) -> str:
        rest = "" if self.inside else self.buffer
        self.buffer = ""
        return rest


def clean_narration(text: str, max_chars: int) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]{0,80}>", "", text)
    text = text.replace("**", "").replace("__", "")
    lines = [ln for ln in text.splitlines() if not _MARKDOWN_LINE.match(ln)]
    text = "\n".join(lines)
    text = _CHOICES_TAIL.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > max_chars:
        cut = text[:max_chars]
        boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("\n"))
        text = cut[: boundary + 1] if boundary > max_chars // 2 else cut.rstrip() + "…"
    return text.strip()


def acceptable(text: str) -> bool:
    return len(text) >= 15 and not _REFUSAL_OR_LEAK.search(text)
