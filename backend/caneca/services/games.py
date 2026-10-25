"""Application service: adventures, turns, memory, checkpoints and import/export.

Database work is synchronous (SQLite) and runs in worker threads; the turn pipeline is
an async generator so narration can stream while the UI stays responsive.

Turn pipeline (docs/architecture/game-engine.md):
    input → intent (parser, optionally refined by AI, validated against the scene)
          → engine.resolve (rules, checks, effects)
          → transactional commit (state + turn + journal, optimistic version check)
          → "outcome" event to the UI
          → narration (AI stream or deterministic text) → saved → "done"
          → incremental summary when due
"""

from __future__ import annotations

import logging
import secrets as pysecrets
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import anyio
from anyio import to_thread
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select, update

from caneca.ai.config import CLOUD_PROVIDERS, AISettings, SecretStore, build_provider
from caneca.ai.orchestrator import Narrator, offline_summary
from caneca.ai.prompts import build_narration_prompt, length_profile
from caneca.ai.providers.base import ProviderError, Usage
from caneca.api.views import event_view, game_view
from caneca.config import APP_VERSION, Settings
from caneca.game.engine import Engine, TurnOutcome
from caneca.game.i18n import tr
from caneca.game.parser import MAX_INPUT_CHARS, Intent
from caneca.game.state import AdventureSettings, MugIdentity, WorldState
from caneca.memory.context import RecentTurn, budget_for, select_memory
from caneca.persistence.db import Database
from caneca.persistence.orm import CheckpointRow, GameRow, JournalRow, SettingRow, TurnRow, utcnow
from caneca.services.saves import SAVE_FORMAT, SAVE_FORMAT_VERSION, validate_save

log = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, code: str, status: int = 400, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.status = status
        self.detail = detail


class CreateGameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    mug: MugIdentity
    settings: AdventureSettings = Field(default_factory=AdventureSettings)
    seed: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class UpdateGameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    settings: AdventureSettings | None = None


class TurnIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verb: str = Field(max_length=16)
    target: str | None = Field(default=None, max_length=80)
    item: str | None = Field(default=None, max_length=80)
    interaction: str | None = Field(default=None, max_length=80)


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    intent: TurnIntent | None = None
    expected_turn: int | None = Field(default=None, ge=0)


@dataclass
class _Committed:
    turn_id: int
    number: int
    version: int
    recent: list[RecentTurn]
    summary: str
    summary_turn: int
    openings: list[str]
    meta: dict[str, Any]


def _status_of(state: WorldState) -> str:
    if state.defeated:
        return "defeated"
    return "ended" if state.ending else "active"


class GameService:
    def __init__(self, db: Database, engine: Engine, settings: Settings) -> None:
        self.db = db
        self.engine = engine
        self.settings = settings
        self.secrets = SecretStore(settings.secrets_path)
        self._busy: set[str] = set()
        self._cancel: dict[str, anyio.Event] = {}
        self.transport: Any = None  # test hook: httpx transport for providers

    # ---------------------------------------------------------------- settings
    def ai_settings(self) -> AISettings:
        with self.db.session() as s:
            row = s.get(SettingRow, "ai")
            if row is None:
                return AISettings(
                    ollama_url=self.settings.ollama_url, openai_base_url=self.settings.openai_base_url
                )
            return AISettings.model_validate(row.value)

    def save_ai_settings(self, ai: AISettings) -> AISettings:
        with self.db.session() as s:
            row = s.get(SettingRow, "ai")
            if row is None:
                s.add(SettingRow(key="ai", value=ai.model_dump()))
            else:
                row.value = ai.model_dump()
        return ai

    def provider_for(self, ai: AISettings, provider_id: str | None = None) -> Any:
        pid = provider_id or ai.provider
        return build_provider(pid, ai, self.secrets, self.settings, self.transport)

    # ------------------------------------------------------------------ games
    def _meta(self, row: GameRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "status": row.status,
            "version": row.version,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }

    def _load(self, s: Any, game_id: str) -> tuple[GameRow, WorldState]:
        row = s.get(GameRow, game_id)
        if row is None:
            raise ServiceError("game_not_found", 404)
        return row, WorldState.model_validate(row.state)

    def view(self, game_id: str, lang: str | None = None) -> dict[str, Any]:
        with self.db.session() as s:
            row, state = self._load(s, game_id)
            return game_view(self.engine, state, lang or state.settings.language, self._meta(row))

    def list_games(self) -> list[dict[str, Any]]:
        w = self.engine.world
        with self.db.session() as s:
            rows = s.scalars(select(GameRow).order_by(GameRow.updated_at.desc())).all()
            out = []
            for row in rows:
                state = WorldState.model_validate(row.state)
                lang = state.settings.language
                loc = w.locations.get(row.location)
                out.append(
                    {
                        **self._meta(row),
                        "turn": row.turn,
                        "chapter": row.chapter,
                        "location": tr(loc.name, lang) if loc else row.location,
                        "mug": state.mug.model_dump(),
                        "level": state.stats.level,
                        "language": lang,
                    }
                )
            return out

    def create_game(self, req: CreateGameRequest) -> dict[str, Any]:
        seed = req.seed or pysecrets.token_hex(6)
        state = self.engine.new_state(req.mug, req.settings, seed)
        lang = req.settings.language
        game_id = str(uuid.uuid4())
        intro = self.engine.intro()
        now = utcnow()
        with self.db.session() as s:
            row = GameRow(
                id=game_id,
                name=req.name.strip(),
                created_at=now,
                updated_at=now,
                state=state.model_dump(mode="json"),
                version=1,
                turn=0,
                chapter=1,
                location=state.location,
                status="active",
                summary="",
                summary_turn=0,
            )
            s.add(row)
            s.add(
                TurnRow(
                    game_id=game_id,
                    number=0,
                    kind="intro",
                    player_input="",
                    intent={},
                    outcome={"messages": [intro], "events": []},
                    narration=tr(intro, lang),
                    fallback=tr(intro, lang),
                    source="engine",
                )
            )
            for ev in self.engine.initial_events(state):
                s.add(self._journal_row(game_id, 0, ev.data))
            s.flush()
            return game_view(self.engine, state, lang, self._meta(row))

    def update_game(self, game_id: str, req: UpdateGameRequest) -> dict[str, Any]:
        with self.db.session() as s:
            row, state = self._load(s, game_id)
            if req.name:
                row.name = req.name.strip()
            if req.settings:
                state.settings = req.settings
                row.state = state.model_dump(mode="json")
                row.version += 1
            row.updated_at = utcnow()
            s.flush()
            return game_view(self.engine, state, state.settings.language, self._meta(row))

    def delete_game(self, game_id: str) -> None:
        with self.db.session() as s:
            row = s.get(GameRow, game_id)
            if row is None:
                raise ServiceError("game_not_found", 404)
            s.delete(row)

    # ---------------------------------------------------------------- history
    def history(self, game_id: str, before: int | None, limit: int, lang: str | None) -> dict[str, Any]:
        limit = max(1, min(limit, 100))
        with self.db.session() as s:
            _row, state = self._load(s, game_id)
            lang = lang or state.settings.language
            q = select(TurnRow).where(TurnRow.game_id == game_id)
            if before is not None:
                q = q.where(TurnRow.number < before)
            rows = s.scalars(q.order_by(TurnRow.number.desc()).limit(limit + 1)).all()
            more = len(rows) > limit
            items = [self._turn_view(t, lang) for t in reversed(rows[:limit])]
            return {"turns": items, "has_more": more}

    def _turn_view(self, t: TurnRow, lang: str) -> dict[str, Any]:
        narration = t.narration
        messages = (t.outcome or {}).get("messages") or []
        if t.source in ("engine", "fallback") and messages:
            narration = "\n\n".join(tr(m, lang) for m in messages if tr(m, lang))
        events = [v for e in (t.outcome or {}).get("events", []) if (v := event_view(self.engine, e, lang))]
        return {
            "number": t.number,
            "kind": t.kind,
            "player_input": t.player_input,
            "narration": narration,
            "source": t.source,
            "events": events,
            "created_at": t.created_at.isoformat(),
        }

    def journal(self, game_id: str, lang: str | None) -> list[dict[str, Any]]:
        w = self.engine.world
        with self.db.session() as s:
            _row, state = self._load(s, game_id)
            lang = lang or state.settings.language
            rows = s.scalars(
                select(JournalRow)
                .where(JournalRow.game_id == game_id)
                .order_by(JournalRow.turn.desc(), JournalRow.id.desc())
            ).all()
            return [
                {
                    "id": r.id,
                    "turn": r.turn,
                    "kind": r.kind,
                    "title": tr(r.title, lang),
                    "body": tr(r.body, lang),
                    "location": tr(w.locations[r.location].name, lang) if r.location in w.locations else "",
                    "participants": [tr(w.npcs[p].name, lang) for p in r.participants if p in w.npcs],
                    "decision": r.decision,
                }
                for r in rows
            ]

    def memories(self, game_id: str, lang: str | None) -> dict[str, Any]:
        w = self.engine.world
        with self.db.session() as s:
            row, state = self._load(s, game_id)
            lang = lang or state.settings.language
            facts = sorted(state.facts.values(), key=lambda f: (-f.importance, -f.turn))
            return {
                "summary": row.summary,
                "facts": [
                    {
                        "id": f.id,
                        "text": tr(f.text, lang),
                        "turn": f.turn,
                        "importance": f.importance,
                        "location": tr(w.locations[f.location].name, lang)
                        if f.location in w.locations
                        else "",
                        "known_by": [
                            tr(w.npcs[n].name, lang) for n, ns in state.npcs.items() if f.id in ns.memories
                        ],
                    }
                    for f in facts
                ],
            }

    # ------------------------------------------------------------------ turns
    def _journal_row(self, game_id: str, turn: int, data: dict[str, Any]) -> JournalRow:
        return JournalRow(
            game_id=game_id,
            turn=turn,
            kind=data.get("entry_kind", "story"),
            title=data["title"],
            body=data["body"],
            location=data["location"],
            participants=list(data.get("participants") or []),
            decision=str(data.get("decision") or "")[:2000],
        )

    def _load_for_turn(self, game_id: str) -> tuple[WorldState, int, str | None, dict[str, Any]]:
        with self.db.session() as s:
            row, state = self._load(s, game_id)
            return state, row.version, row.last_npc, self._meta(row)

    def _commit_turn(
        self, game_id: str, version: int, outcome: TurnOutcome, player_input: str, memory_turns: int
    ) -> _Committed:
        state = outcome.state
        lang = state.settings.language
        fallback = outcome.narration(lang)
        with self.db.session() as s:
            res = s.execute(
                update(GameRow)
                .where(GameRow.id == game_id, GameRow.version == version)
                .values(
                    state=state.model_dump(mode="json"),
                    version=version + 1,
                    turn=state.turn,
                    chapter=state.chapter,
                    location=state.location,
                    status=_status_of(state),
                    updated_at=utcnow(),
                    last_npc=outcome.dialogue_npc,
                )
            )
            if res.rowcount != 1:  # type: ignore[attr-defined]
                raise ServiceError("conflict", 409, "a partida mudou em outra janela")
            turn = TurnRow(
                game_id=game_id,
                number=state.turn,
                kind="action",
                player_input=player_input,
                intent=outcome.intent.model_dump(),
                outcome={
                    "messages": outcome.messages,
                    "events": [e.as_dict() for e in outcome.events],
                    "check": outcome.check.as_dict() if outcome.check else None,
                    "success": outcome.success,
                    "meta": outcome.meta,
                    "minutes": outcome.minutes,
                    "dialogue_npc": outcome.dialogue_npc,
                    "topic": outcome.topic,
                },
                narration=fallback,
                fallback=fallback,
                source="engine",
            )
            s.add(turn)
            for ev in outcome.events:
                if ev.kind == "journal":
                    s.add(self._journal_row(game_id, state.turn, ev.data))
                if ev.kind == "chapter":
                    chapter = self.engine.world.chapters[ev.data["chapter"]]
                    s.add(
                        CheckpointRow(
                            game_id=game_id,
                            label=tr(chapter.title, lang)[:80],
                            turn=state.turn,
                            state=state.model_dump(mode="json"),
                            summary="",
                            auto=True,
                        )
                    )
            s.flush()
            game = s.get(GameRow, game_id)
            assert game is not None
            recent_rows = s.scalars(
                select(TurnRow)
                .where(TurnRow.game_id == game_id, TurnRow.number < state.turn, TurnRow.kind == "action")
                .order_by(TurnRow.number.desc())
                .limit(max(memory_turns, 3))
            ).all()
            recent = (
                [RecentTurn(t.number, t.player_input, t.narration) for t in reversed(recent_rows)][
                    -memory_turns:
                ]
                if memory_turns
                else []
            )
            openings = [t.narration[:60] for t in recent_rows[:3] if t.narration]
            return _Committed(
                turn.id,
                state.turn,
                version + 1,
                recent,
                game.summary,
                game.summary_turn,
                openings,
                self._meta(game),
            )

    def _save_narration(
        self, turn_id: int, text: str, source: str, provider: str | None, model: str | None, usage: Usage
    ) -> None:
        with self.db.session() as s:
            t = s.get(TurnRow, turn_id)
            if t is None:
                return
            t.narration = text
            t.source = source
            t.provider = provider
            t.model = model
            t.tokens_in = usage.tokens_in
            t.tokens_out = usage.tokens_out

    def cancel(self, game_id: str) -> bool:
        ev = self._cancel.get(game_id)
        if ev is None:
            return False
        ev.set()
        return True

    def _intent_from_request(self, state: WorldState, req: TurnRequest, last_npc: str | None) -> Intent:
        if req.intent is not None:
            try:
                return Intent(
                    verb=req.intent.verb,
                    target=req.intent.target,
                    item=req.intent.item,
                    interaction=req.intent.interaction,
                    raw=req.text,
                    source="suggestion",
                )
            except ValueError as exc:
                raise ServiceError("invalid_intent", 422, str(exc)) from exc
        return self.engine.interpret(state, req.text, last_npc)

    async def play_turn(
        self, game_id: str, req: TurnRequest
    ) -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
        # A plain set (not a task-owned lock): the HTTP layer may resume this generator
        # from a different task while streaming. The event loop is single-threaded.
        if game_id in self._busy:
            raise ServiceError("turn_in_progress", 409)
        self._busy.add(game_id)
        cancel = anyio.Event()
        self._cancel[game_id] = cancel
        try:
            async for item in self._play_turn(game_id, req, cancel):
                yield item
        finally:
            self._cancel.pop(game_id, None)
            self._busy.discard(game_id)

    async def _play_turn(
        self, game_id: str, req: TurnRequest, cancel: anyio.Event
    ) -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
        state, version, last_npc, meta = await to_thread.run_sync(self._load_for_turn, game_id)
        if req.expected_turn is not None and req.expected_turn != state.turn:
            raise ServiceError("conflict", 409, "turno desatualizado")
        lang = state.settings.language
        ai = await to_thread.run_sync(self.ai_settings)
        provider_id = ai.provider
        if provider_id in CLOUD_PROVIDERS and not ai.cloud_consent:
            provider_id = "offline"
        provider = self.provider_for(ai, provider_id) if provider_id != "offline" else None
        narrator = Narrator(provider, ai, provider_id) if provider and ai.model_for(provider_id) else None

        intent = self._intent_from_request(state, req, last_npc)
        if (
            narrator
            and ai.ai_intent
            and intent.source == "parser"
            and intent.confidence < 0.6
            and not intent.injection
        ):
            intent = await narrator.refine_intent(self.engine, state, req.text, intent)

        outcome = self.engine.resolve(state, intent)
        if outcome.meta and outcome.state.turn == state.turn:
            # Game already finished: nothing to persist.
            yield "outcome", self._outcome_payload(outcome, meta, lang, None)
            yield "done", {"narration": outcome.narration(lang), "source": "engine"}
            return
        committed = await to_thread.run_sync(
            self._commit_turn, game_id, version, outcome, req.text, ai.memory_turns
        )
        yield "outcome", self._outcome_payload(outcome, committed.meta, lang, committed.number)

        fallback = outcome.narration(lang)
        if narrator is None or outcome.meta or outcome.intent.verb in ("inventory", "status", "help"):
            yield "done", {"narration": fallback, "source": "engine"}
            await self._maybe_summarize(game_id, committed, narrator, ai, lang)
            return

        memory = select_memory(
            outcome.state,
            lang,
            self._scene_ids(outcome.state),
            req.text,
            committed.recent,
            committed.summary,
            budget_for(
                ai.context_tokens, length_profile(outcome.state.settings.narrative_length, outcome)[0]
            ),
            npc_id=outcome.dialogue_npc,
        )
        prompt = build_narration_prompt(self.engine, outcome.state, outcome, memory, committed.openings)
        sink: list[str] = []
        usage = Usage()
        source, text, error = "ai", fallback, None
        try:
            async for delta in narrator.stream_narration(prompt, fallback, cancel, sink):
                yield "delta", {"text": delta}
            usage = narrator.last_usage
            if cancel.is_set():
                source = "cancelled"
                text = "".join(sink).strip() or fallback
            else:
                text, ok = narrator.finalize("".join(sink), fallback, prompt.max_tokens)
                source = "ai" if ok else "fallback"
        except ProviderError as exc:
            error = exc
            source, text = "fallback", fallback
        except anyio.get_cancelled_exc_class():
            with anyio.CancelScope(shield=True):
                partial = "".join(sink).strip()
                await to_thread.run_sync(
                    self._save_narration,
                    committed.turn_id,
                    partial or fallback,
                    "cancelled",
                    provider_id,
                    narrator.model,
                    usage,
                )
            raise
        await to_thread.run_sync(
            self._save_narration, committed.turn_id, text, source, provider_id, narrator.model, usage
        )
        if error is not None:
            yield "warning", {"code": f"ai_{error.code}", "detail": error.message}
        yield (
            "done",
            {
                "narration": text,
                "source": source,
                "usage": {"tokens_in": usage.tokens_in, "tokens_out": usage.tokens_out},
            },
        )
        await self._maybe_summarize(game_id, committed, narrator, ai, lang)

    def _scene_ids(self, state: WorldState) -> set[str]:
        ids = {state.location, self.engine.world.locations[state.location].region}
        ids |= set(self.engine.present_npcs(state)) | set(state.inventory())
        ids |= set(state.items_at(state.location))
        return ids

    def _outcome_payload(
        self, outcome: TurnOutcome, meta: dict[str, Any], lang: str, number: int | None
    ) -> dict[str, Any]:
        return {
            "turn": number,
            "intent": outcome.intent.model_dump(include={"verb", "target", "item", "source"}),
            "check": outcome.check.as_dict() if outcome.check else None,
            "success": outcome.success,
            "fallback": outcome.narration(lang),
            "events": [v for e in outcome.events if (v := event_view(self.engine, e, lang))],
            "view": game_view(self.engine, outcome.state, lang, meta),
        }

    async def _maybe_summarize(
        self, game_id: str, committed: _Committed, narrator: Narrator | None, ai: AISettings, lang: str
    ) -> None:
        if committed.number - committed.summary_turn < ai.summary_every:
            return

        def entries() -> list[str]:
            with self.db.session() as s:
                rows = s.scalars(
                    select(JournalRow)
                    .where(
                        JournalRow.game_id == game_id,
                        JournalRow.turn > committed.summary_turn,
                    )
                    .order_by(JournalRow.turn)
                ).all()
                lines = [f"{tr(r.title, lang)}: {tr(r.body, lang)}" for r in rows]
                turns = s.scalars(
                    select(TurnRow)
                    .where(
                        TurnRow.game_id == game_id,
                        TurnRow.number > committed.summary_turn,
                        TurnRow.kind == "action",
                    )
                    .order_by(TurnRow.number)
                ).all()
                lines += [f"[{t.player_input[:80]}] {t.narration[:160]}" for t in turns[-8:]]
                return lines

        lines = await to_thread.run_sync(entries)
        summary = None
        if narrator is not None:
            with anyio.move_on_after(ai.timeout_seconds):
                summary = await narrator.summarize(lang, committed.summary, lines)
        if summary is None:
            summary = offline_summary(lang, committed.summary, lines[:6])

        def store() -> None:
            with self.db.session() as s:
                s.execute(
                    update(GameRow)
                    .where(GameRow.id == game_id)
                    .values(summary=summary[:4000], summary_turn=committed.number)
                )

        await to_thread.run_sync(store)

    # ------------------------------------------------------------ checkpoints
    def list_checkpoints(self, game_id: str) -> list[dict[str, Any]]:
        with self.db.session() as s:
            self._load(s, game_id)
            rows = s.scalars(
                select(CheckpointRow)
                .where(CheckpointRow.game_id == game_id)
                .order_by(CheckpointRow.created_at.desc())
            ).all()
            return [
                {
                    "id": r.id,
                    "label": r.label,
                    "turn": r.turn,
                    "auto": r.auto,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]

    def create_checkpoint(self, game_id: str, label: str, auto: bool = False) -> dict[str, Any]:
        with self.db.session() as s:
            row, state = self._load(s, game_id)
            cp = CheckpointRow(
                game_id=game_id,
                label=label.strip()[:80] or "Save",
                turn=state.turn,
                state=row.state,
                summary=row.summary,
                auto=auto,
            )
            s.add(cp)
            s.flush()
            return {
                "id": cp.id,
                "label": cp.label,
                "turn": cp.turn,
                "auto": cp.auto,
                "created_at": cp.created_at.isoformat(),
            }

    def restore_checkpoint(self, game_id: str, checkpoint_id: int) -> dict[str, Any]:
        """Rewinds the adventure. The current point is kept as an automatic checkpoint."""
        with self.db.session() as s:
            row, current = self._load(s, game_id)
            cp = s.get(CheckpointRow, checkpoint_id)
            if cp is None or cp.game_id != game_id:
                raise ServiceError("checkpoint_not_found", 404)
            lang = current.settings.language
            label = "Antes de restaurar" if lang == "pt-BR" else "Before restoring"
            s.add(
                CheckpointRow(
                    game_id=game_id,
                    label=f"{label} (t{current.turn})",
                    turn=current.turn,
                    state=row.state,
                    summary=row.summary,
                    auto=True,
                )
            )
            state = WorldState.model_validate(cp.state)
            s.execute(delete(TurnRow).where(TurnRow.game_id == game_id, TurnRow.number > cp.turn))
            s.execute(delete(JournalRow).where(JournalRow.game_id == game_id, JournalRow.turn > cp.turn))
            row.state = cp.state
            row.version += 1
            row.turn = state.turn
            row.chapter = state.chapter
            row.location = state.location
            row.status = _status_of(state)
            row.summary = cp.summary
            row.summary_turn = min(row.summary_turn, cp.turn)
            row.last_npc = None
            row.updated_at = utcnow()
            s.flush()
            return game_view(self.engine, state, lang, self._meta(row))

    def delete_checkpoint(self, game_id: str, checkpoint_id: int) -> None:
        with self.db.session() as s:
            cp = s.get(CheckpointRow, checkpoint_id)
            if cp is None or cp.game_id != game_id:
                raise ServiceError("checkpoint_not_found", 404)
            s.delete(cp)

    # ---------------------------------------------------------- import/export
    def export_game(self, game_id: str) -> dict[str, Any]:
        with self.db.session() as s:
            row, state = self._load(s, game_id)
            turns = s.scalars(
                select(TurnRow).where(TurnRow.game_id == game_id).order_by(TurnRow.number)
            ).all()
            journal = s.scalars(
                select(JournalRow).where(JournalRow.game_id == game_id).order_by(JournalRow.id)
            ).all()
            cps = s.scalars(
                select(CheckpointRow).where(CheckpointRow.game_id == game_id).order_by(CheckpointRow.id)
            ).all()
            return {
                "format": SAVE_FORMAT,
                "format_version": SAVE_FORMAT_VERSION,
                "app_version": APP_VERSION,
                "content_version": state.content_version,
                "exported_at": datetime.now(UTC).isoformat(),
                "game": {
                    "name": row.name,
                    "created_at": row.created_at.isoformat(),
                    "status": row.status,
                    "state": row.state,
                    "summary": row.summary,
                    "summary_turn": row.summary_turn,
                    "last_npc": row.last_npc,
                },
                "turns": [
                    {
                        "number": t.number,
                        "kind": t.kind,
                        "created_at": t.created_at.isoformat(),
                        "player_input": t.player_input,
                        "intent": t.intent,
                        "outcome": t.outcome,
                        "narration": t.narration,
                        "fallback": t.fallback,
                        "source": t.source,
                        "provider": t.provider,
                        "model": t.model,
                        "tokens_in": t.tokens_in,
                        "tokens_out": t.tokens_out,
                    }
                    for t in turns
                ],
                "journal": [
                    {
                        "turn": j.turn,
                        "kind": j.kind,
                        "title": j.title,
                        "body": j.body,
                        "location": j.location,
                        "participants": j.participants,
                        "decision": j.decision,
                        "created_at": j.created_at.isoformat(),
                    }
                    for j in journal
                ],
                "checkpoints": [
                    {
                        "label": c.label,
                        "turn": c.turn,
                        "state": c.state,
                        "summary": c.summary,
                        "auto": c.auto,
                        "created_at": c.created_at.isoformat(),
                    }
                    for c in cps
                ],
            }

    def import_game(self, raw: Any) -> dict[str, Any]:
        try:
            save = validate_save(raw, self.engine.world)
        except ValueError as exc:
            raise ServiceError("invalid_save", 422, str(exc)) from exc
        game_id = str(uuid.uuid4())
        g = save.game
        now = utcnow()
        with self.db.session() as s:
            row = GameRow(
                id=game_id,
                name=g.name,
                created_at=g.created_at,
                updated_at=now,
                state=g.state.model_dump(mode="json"),
                version=1,
                turn=g.state.turn,
                chapter=g.state.chapter,
                location=g.state.location,
                status=g.status,
                summary=g.summary,
                summary_turn=g.summary_turn,
                last_npc=None,
            )
            s.add(row)
            for t in save.turns:
                s.add(TurnRow(game_id=game_id, **t.model_dump()))
            for j in save.journal:
                s.add(JournalRow(game_id=game_id, **j.model_dump()))
            for c in save.checkpoints:
                data = c.model_dump()
                data["state"] = c.state.model_dump(mode="json")
                s.add(CheckpointRow(game_id=game_id, **data))
            s.flush()
            return game_view(self.engine, g.state, g.state.settings.language, self._meta(row))

    # ------------------------------------------------------------------ usage
    def usage(self) -> list[dict[str, Any]]:
        with self.db.session() as s:
            rows = s.execute(
                select(
                    TurnRow.provider,
                    TurnRow.model,
                    func.count(),
                    func.sum(TurnRow.tokens_in),
                    func.sum(TurnRow.tokens_out),
                )
                .where(TurnRow.provider.is_not(None))
                .group_by(TurnRow.provider, TurnRow.model)
            ).all()
            return [
                {"provider": p, "model": m, "turns": n, "tokens_in": int(ti or 0), "tokens_out": int(to or 0)}
                for p, m, n, ti, to in rows
            ]
