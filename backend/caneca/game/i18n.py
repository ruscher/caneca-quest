"""Localized text primitives shared by the content, the engine and the API.

Every player-facing string produced by the engine is an ``LText``: a mapping with one
entry per supported language. Rendering to a single language happens at the edges
(API views, narrator prompts), never inside the rules.
"""

from __future__ import annotations

from typing import Annotated, Literal, get_args

from pydantic import AfterValidator

Lang = Literal["pt-BR", "en"]
LANGS: tuple[Lang, ...] = get_args(Lang)
DEFAULT_LANG: Lang = "pt-BR"


def _require_all_langs(value: dict[str, str]) -> dict[str, str]:
    missing = [lang for lang in LANGS if not value.get(lang, "").strip()]
    if missing:
        raise ValueError(f"texto sem tradução para: {', '.join(missing)}")
    return value


LText = Annotated[dict[str, str], AfterValidator(_require_all_langs)]


def tr(text: dict[str, str] | None, lang: str) -> str:
    """Render a localized text, falling back to the default language."""
    if not text:
        return ""
    return text.get(lang) or text.get(DEFAULT_LANG) or next(iter(text.values()), "")


def lt(pt: str, en: str) -> dict[str, str]:
    return {"pt-BR": pt, "en": en}


def fmt(text: dict[str, str], **params: object) -> dict[str, str]:
    """Apply ``str.format`` params to every language of a localized text."""
    out: dict[str, str] = {}
    for lang, value in text.items():
        localized = {k: (tr(v, lang) if isinstance(v, dict) else v) for k, v in params.items()}
        out[lang] = value.format(**localized)
    return out


def join(parts: list[dict[str, str]], sep: str = " ") -> dict[str, str]:
    return {lang: sep.join(tr(p, lang) for p in parts if tr(p, lang)) for lang in LANGS}
