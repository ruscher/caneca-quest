"""Versioned export/import of adventures. Imports are validated before touching the DB."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from caneca.game.state import INVENTORY, VOID, WorldState
from caneca.game.world import World

SAVE_FORMAT = "caneca-quest-save"
SAVE_FORMAT_VERSION = 1


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExportTurn(_Strict):
    number: int = Field(ge=0)
    kind: Literal["intro", "action"]
    created_at: datetime
    player_input: str = Field(max_length=2000)
    intent: dict[str, Any]
    outcome: dict[str, Any]
    narration: str = Field(max_length=20000)
    fallback: str = Field(max_length=20000)
    source: str = Field(max_length=16)
    provider: str | None = Field(default=None, max_length=32)
    model: str | None = Field(default=None, max_length=128)
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)


class ExportJournal(_Strict):
    turn: int = Field(ge=0)
    kind: str = Field(max_length=24)
    title: dict[str, str]
    body: dict[str, str]
    location: str = Field(max_length=64)
    participants: list[str]
    decision: str = Field(max_length=2000)
    created_at: datetime


class ExportCheckpoint(_Strict):
    label: str = Field(max_length=80)
    turn: int = Field(ge=0)
    state: WorldState
    summary: str = Field(max_length=20000)
    auto: bool
    created_at: datetime


class ExportGame(_Strict):
    name: str = Field(min_length=1, max_length=80)
    created_at: datetime
    status: Literal["active", "ended", "defeated"]
    state: WorldState
    summary: str = Field(max_length=20000)
    summary_turn: int = Field(ge=0)
    last_npc: str | None = Field(default=None, max_length=64)


class SaveFile(_Strict):
    format: Literal["caneca-quest-save"]
    format_version: int
    app_version: str = Field(max_length=32)
    content_version: str = Field(max_length=32)
    exported_at: datetime
    game: ExportGame
    turns: list[ExportTurn] = Field(max_length=20000)
    journal: list[ExportJournal] = Field(max_length=20000)
    checkpoints: list[ExportCheckpoint] = Field(max_length=200)


class ImportError_(ValueError):
    """Raised when an imported save is not compatible or not consistent."""


def check_state_against_world(state: WorldState, world: World) -> list[str]:
    errors: list[str] = []
    if state.location not in world.locations:
        errors.append(f"local desconhecido: {state.location}")
    for item, where in state.item_locations.items():
        if item not in world.items:
            errors.append(f"item desconhecido: {item}")
        valid = (
            where in (INVENTORY, VOID)
            or where in world.locations
            or (where.startswith("npc:") and where[4:] in world.npcs)
        )
        if not valid:
            errors.append(f"posição inválida para {item}: {where}")
    for npc_id, npc in state.npcs.items():
        if npc_id not in world.npcs:
            errors.append(f"personagem desconhecido: {npc_id}")
        if npc.location not in world.locations and npc.location != VOID:
            errors.append(f"local inválido para {npc_id}")
        if not -100 <= npc.relationship <= 100:
            errors.append(f"relação fora do intervalo: {npc_id}")
    errors += [f"missão desconhecida: {q}" for q in state.quests if q not in world.quests]
    errors += [f"habilidade desconhecida: {a}" for a in state.abilities if a not in world.abilities]
    errors += [f"conquista desconhecida: {a}" for a in state.achievements if a not in world.achievements]
    if state.ending and state.ending not in world.endings:
        errors.append(f"final desconhecido: {state.ending}")
    if state.chapter not in world.chapters:
        errors.append(f"capítulo desconhecido: {state.chapter}")
    for name in ("temperature", "coffee", "integrity", "energy", "courage", "creativity"):
        value = getattr(state.stats, name)
        if not -10 <= value <= 100:
            errors.append(f"atributo fora do intervalo: {name}")
    return errors


def validate_save(raw: Any, world: World) -> SaveFile:
    try:
        save = SaveFile.model_validate(raw)
    except ValueError as exc:
        raise ImportError_(f"arquivo inválido: {exc}") from exc
    if save.format_version > SAVE_FORMAT_VERSION:
        raise ImportError_("este arquivo foi criado por uma versão mais nova do jogo")
    major = save.content_version.split(".")[0]
    if major != world.meta.content_version.split(".")[0]:
        raise ImportError_("versão de conteúdo incompatível")
    errors = check_state_against_world(save.game.state, world)
    for cp in save.checkpoints:
        errors += check_state_against_world(cp.state, world)
    if errors:
        raise ImportError_("estado inconsistente: " + "; ".join(errors[:8]))
    numbers = [t.number for t in save.turns]
    if len(numbers) != len(set(numbers)):
        raise ImportError_("turnos duplicados")
    return save
