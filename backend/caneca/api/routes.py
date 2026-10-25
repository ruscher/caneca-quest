"""REST + SSE endpoints."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any, Literal

from anyio import to_thread
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from caneca.ai.config import CLOUD_PROVIDERS, AISettings, build_provider
from caneca.ai.providers.base import ChatMessage, GenerationParams, ProviderError, Usage
from caneca.config import APP_VERSION
from caneca.game.i18n import LANGS
from caneca.game.state import (
    AdventureSettings,
    Difficulty,
    Drink,
    Material,
    NarrativeLength,
    Personality,
    Style,
    Tone,
    Trait,
)
from caneca.services.games import (
    CreateGameRequest,
    GameService,
    ServiceError,
    TurnRequest,
    UpdateGameRequest,
)

router = APIRouter(prefix="/api")

Lang = Literal["pt-BR", "en"]


def svc(request: Request) -> GameService:
    service: GameService = request.app.state.games
    return service


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    world = svc(request).engine.world
    return {"status": "ok", "version": APP_VERSION, "content_version": world.meta.content_version}


@router.get("/meta")
async def meta() -> dict[str, Any]:
    def values(t: Any) -> list[str]:
        return list(t.__args__)

    return {
        "version": APP_VERSION,
        "languages": list(LANGS),
        "options": {
            "tone": values(Tone),
            "difficulty": values(Difficulty),
            "narrative_length": values(NarrativeLength),
            "material": values(Material),
            "drink": values(Drink),
            "style": values(Style),
            "personality": values(Personality),
            "trait": values(Trait),
        },
        "colors": ["#f4efe6", "#2f2a28", "#b4472f", "#2f5d8a", "#3f7a5a", "#d9a441", "#8a4f7d", "#c97b84"],
        "defaults": AdventureSettings().model_dump(),
    }


# ------------------------------------------------------------------------------ games
@router.get("/games")
async def list_games(request: Request) -> list[dict[str, Any]]:
    return await to_thread.run_sync(svc(request).list_games)


@router.post("/games", status_code=201)
async def create_game(request: Request, body: CreateGameRequest) -> dict[str, Any]:
    return await to_thread.run_sync(svc(request).create_game, body)


@router.post("/games/import", status_code=201)
async def import_game(request: Request) -> dict[str, Any]:
    raw = await request.body()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ServiceError("invalid_save", 422, "JSON inválido") from exc
    return await to_thread.run_sync(svc(request).import_game, data)


@router.get("/games/{game_id}")
async def get_game(request: Request, game_id: str, lang: Lang | None = None) -> dict[str, Any]:
    return await to_thread.run_sync(svc(request).view, game_id, lang)


@router.patch("/games/{game_id}")
async def update_game(request: Request, game_id: str, body: UpdateGameRequest) -> dict[str, Any]:
    return await to_thread.run_sync(svc(request).update_game, game_id, body)


@router.delete("/games/{game_id}", status_code=204)
async def delete_game(request: Request, game_id: str) -> None:
    await to_thread.run_sync(svc(request).delete_game, game_id)


@router.get("/games/{game_id}/turns")
async def history(
    request: Request,
    game_id: str,
    before: int | None = None,
    limit: int = Query(30, ge=1, le=100),
    lang: Lang | None = None,
) -> dict[str, Any]:
    return await to_thread.run_sync(svc(request).history, game_id, before, limit, lang)


def _sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


@router.post("/games/{game_id}/turns", response_model=None)
async def play_turn(
    request: Request, game_id: str, body: TurnRequest, stream: bool = True
) -> StreamingResponse | JSONResponse:
    agen = svc(request).play_turn(game_id, body)
    # Pull the first event before answering so validation/lock/conflict errors become
    # proper HTTP status codes instead of an SSE error frame.
    first = await agen.__anext__()

    if not stream:
        result: dict[str, Any] = {first[0]: first[1]}
        warnings: list[dict[str, Any]] = []
        async for name, data in agen:
            if name == "warning":
                warnings.append(data)
            elif name != "delta":
                result[name] = data
        result["warnings"] = warnings
        return JSONResponse(result)

    async def body_iter() -> AsyncIterator[bytes]:
        yield _sse(first[0], first[1])
        try:
            async for name, data in agen:
                yield _sse(name, data)
        except ServiceError as exc:
            yield _sse("error", {"code": exc.code, "detail": exc.detail})
        except Exception:
            request.app.state.log.exception("turn stream failed")
            yield _sse("error", {"code": "internal"})
        finally:
            await agen.aclose()

    return StreamingResponse(
        body_iter(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/games/{game_id}/cancel")
async def cancel_turn(request: Request, game_id: str) -> dict[str, bool]:
    return {"cancelled": svc(request).cancel(game_id)}


@router.get("/games/{game_id}/journal")
async def journal(request: Request, game_id: str, lang: Lang | None = None) -> list[dict[str, Any]]:
    return await to_thread.run_sync(svc(request).journal, game_id, lang)


@router.get("/games/{game_id}/memories")
async def memories(request: Request, game_id: str, lang: Lang | None = None) -> dict[str, Any]:
    return await to_thread.run_sync(svc(request).memories, game_id, lang)


class CheckpointBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=80)


@router.get("/games/{game_id}/checkpoints")
async def list_checkpoints(request: Request, game_id: str) -> list[dict[str, Any]]:
    return await to_thread.run_sync(svc(request).list_checkpoints, game_id)


@router.post("/games/{game_id}/checkpoints", status_code=201)
async def create_checkpoint(request: Request, game_id: str, body: CheckpointBody) -> dict[str, Any]:
    return await to_thread.run_sync(svc(request).create_checkpoint, game_id, body.label)


@router.post("/games/{game_id}/checkpoints/{checkpoint_id}/restore")
async def restore_checkpoint(request: Request, game_id: str, checkpoint_id: int) -> dict[str, Any]:
    return await to_thread.run_sync(svc(request).restore_checkpoint, game_id, checkpoint_id)


@router.delete("/games/{game_id}/checkpoints/{checkpoint_id}", status_code=204)
async def delete_checkpoint(request: Request, game_id: str, checkpoint_id: int) -> None:
    await to_thread.run_sync(svc(request).delete_checkpoint, game_id, checkpoint_id)


@router.get("/games/{game_id}/export")
async def export_game(request: Request, game_id: str) -> JSONResponse:
    data = await to_thread.run_sync(svc(request).export_game, game_id)
    safe = "".join(c for c in data["game"]["name"] if c.isalnum() or c in "-_ ")[:40].strip() or "aventura"
    return JSONResponse(
        data,
        headers={
            "Content-Disposition": f'attachment; filename="caneca-quest-{safe}.json"',
        },
    )


# --------------------------------------------------------------------------------- AI
def _ai_payload(service: GameService, ai: AISettings) -> dict[str, Any]:
    return {
        **ai.model_dump(),
        "keys": {p: service.secrets.source(p) for p in CLOUD_PROVIDERS},
    }


@router.get("/ai/settings")
async def get_ai_settings(request: Request) -> dict[str, Any]:
    service = svc(request)
    ai = await to_thread.run_sync(service.ai_settings)
    return _ai_payload(service, ai)


@router.put("/ai/settings")
async def put_ai_settings(request: Request, body: AISettings) -> dict[str, Any]:
    service = svc(request)
    ai = await to_thread.run_sync(service.save_ai_settings, body)
    return _ai_payload(service, ai)


@router.get("/ai/status")
async def ai_status(
    request: Request, provider: Literal["ollama", "openai", "anthropic"] | None = None
) -> dict[str, Any]:
    service = svc(request)
    ai = await to_thread.run_sync(service.ai_settings)
    pid = provider or (ai.provider if ai.provider != "offline" else "ollama")
    prov = build_provider(pid, ai, service.secrets, service.settings, service.transport)
    assert prov is not None
    status = await prov.status()
    model = ai.model_for(pid)
    return {
        "provider": pid,
        "available": status.available,
        "detail": status.detail,
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "size_bytes": m.size_bytes,
                "parameter_size": m.details.get("parameter_size"),
                "family": m.details.get("family"),
            }
            for m in status.models
        ],
        "selected_model": model,
        "selected_model_installed": any(m.id == model or m.name == model for m in status.models),
        "external": pid in CLOUD_PROVIDERS,
    }


class TestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["ollama", "openai", "anthropic"]
    model: str = Field(min_length=1, max_length=200)


@router.post("/ai/test")
async def ai_test(request: Request, body: TestBody) -> dict[str, Any]:
    service = svc(request)
    ai = await to_thread.run_sync(service.ai_settings)
    prov = build_provider(body.provider, ai, service.secrets, service.settings, service.transport)
    assert prov is not None
    started = time.monotonic()
    usage = Usage()
    try:
        text = await prov.complete(
            [
                ChatMessage("system", "Reply with one short friendly sentence."),
                ChatMessage("user", "Say hello to a living coffee mug."),
            ],
            GenerationParams(
                model=body.model,
                max_tokens=40,
                temperature=0.5,
                context_tokens=1024,
                timeout=min(ai.timeout_seconds, 120),
            ),
            usage,
        )
    except ProviderError as exc:
        return {"ok": False, "code": exc.code, "detail": exc.message}
    return {
        "ok": True,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "sample": text.strip()[:200],
        "tokens_out": usage.tokens_out,
    }


class KeyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=8, max_length=400, pattern=r"^[\x21-\x7e]+$")


@router.put("/ai/keys/{provider}", status_code=204)
async def set_key(request: Request, provider: Literal["openai", "anthropic"], body: KeyBody) -> None:
    await to_thread.run_sync(svc(request).secrets.set, provider, body.key)


@router.delete("/ai/keys/{provider}", status_code=204)
async def delete_key(request: Request, provider: Literal["openai", "anthropic"]) -> None:
    await to_thread.run_sync(svc(request).secrets.set, provider, None)


@router.get("/ai/usage")
async def ai_usage(request: Request) -> list[dict[str, Any]]:
    return await to_thread.run_sync(svc(request).usage)


# ----------------------------------------------------------------------------- system
@router.post("/system/backup", status_code=201)
async def backup(request: Request) -> dict[str, Any]:
    service = svc(request)
    path = await to_thread.run_sync(
        lambda: service.db.backup(service.settings.backup_dir, service.settings.backups_to_keep)
    )
    return {"file": path.name, "size_bytes": path.stat().st_size}


@router.get("/system/backups")
async def backups(request: Request) -> list[dict[str, Any]]:
    service = svc(request)
    files = await to_thread.run_sync(service.db.list_backups, service.settings.backup_dir)
    return [{"file": p.name, "size_bytes": p.stat().st_size} for p in files]
