"""Shared helpers for engine-level tests (no HTTP)."""

from __future__ import annotations

from collections.abc import Callable

from caneca.game.engine import Engine, TurnOutcome
from caneca.game.parser import Intent
from caneca.game.state import AdventureSettings, MugIdentity, WorldState


def fresh(engine: Engine, location: str | None = None, seed: str = "teste", **settings: object) -> WorldState:
    state = engine.new_state(
        MugIdentity(name="Aurora", color="#f4efe6"),
        AdventureSettings(**settings),  # type: ignore[arg-type]
        seed,
    )
    if location:
        put(state, location)
    return state


def put(state: WorldState, location: str) -> WorldState:
    state.location = location
    if location not in state.visited:
        state.visited.append(location)
    return state


def say(engine: Engine, state: WorldState, text: str, last_npc: str | None = None) -> TurnOutcome:
    return engine.resolve(state, engine.interpret(state, text, last_npc))


def do(
    engine: Engine,
    state: WorldState,
    verb: str,
    target: str | None = None,
    item: str | None = None,
    interaction: str | None = None,
    raw: str = "",
) -> TurnOutcome:
    intent = Intent(
        verb=verb,
        target=target,
        item=item,
        interaction=interaction,  # type: ignore[arg-type]
        raw=raw,
        source="suggestion",
    )
    return engine.resolve(state, intent)


def kinds(outcome: TurnOutcome) -> list[str]:
    return [e.kind for e in outcome.events]


def until(
    engine: Engine, state: WorldState, text: str, done: Callable[[WorldState], bool], tries: int = 12
) -> WorldState:
    """Repeat a risky free-text action until it succeeds (deterministic for a given seed)."""
    for _ in range(tries):
        state = say(engine, state, text).state
        state.stats.energy = 100.0  # keep the test about the puzzle, not about fatigue
        if done(state):
            return state
    raise AssertionError(f"'{text}' never succeeded")
