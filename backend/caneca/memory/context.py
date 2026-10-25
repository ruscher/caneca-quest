"""Memory selection for the narrator.

Layers (see docs/ai/memory.md):
  * immediate  — the last few turns (player input + narration excerpts)
  * episodic   — journal entries (quests, discoveries, story beats)
  * long-term  — facts in the world state, with importance and tags
  * world      — the authoritative state itself (location, items, NPCs)
  * summary    — an incremental summary of older turns

Retrieval is structured and deterministic: facts are scored by importance, overlap with
the entities in the current scene, keyword overlap with the player's words and recency,
then packed into a character budget derived from the configured context size.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from caneca.game.i18n import tr
from caneca.game.parser import normalize
from caneca.game.state import Fact, WorldState

CHARS_PER_TOKEN = 4


@dataclass
class RecentTurn:
    number: int
    player_input: str
    narration: str


@dataclass
class MemoryContext:
    summary: str = ""
    facts: list[str] = field(default_factory=list)
    recent: list[RecentTurn] = field(default_factory=list)
    npc_memories: list[str] = field(default_factory=list)
    used_chars: int = 0
    budget_chars: int = 0
    dropped_facts: int = 0


def budget_for(context_tokens: int, reserved_output_tokens: int) -> int:
    """Characters available for memory, after the fixed prompt parts and the reply."""
    usable = max(512, context_tokens - reserved_output_tokens - 1200)
    return int(usable * CHARS_PER_TOKEN * 0.45)


def score_fact(fact: Fact, scene_ids: set[str], words: set[str], turn: int) -> float:
    score = fact.importance * 2.0
    score += 3.0 * len(scene_ids.intersection(fact.tags))
    if fact.location in scene_ids:
        score += 1.5
    text_words = set(normalize(" ".join(fact.text.values())).split())
    score += 0.8 * len(words.intersection(text_words))
    age = max(0, turn - fact.turn)
    score += 2.0 / (1 + age / 5)
    return score


def select_memory(
    state: WorldState,
    lang: str,
    scene_ids: set[str],
    player_input: str,
    recent: list[RecentTurn],
    summary: str,
    budget_chars: int,
    npc_id: str | None = None,
) -> MemoryContext:
    ctx = MemoryContext(budget_chars=budget_chars)
    remaining = budget_chars

    def take(text: str) -> bool:
        nonlocal remaining
        if len(text) + 2 > remaining:
            return False
        remaining -= len(text) + 2
        return True

    # 1. Summary first (it protects essential older information), capped at 30%.
    if summary:
        cap = max(200, budget_chars * 3 // 10)
        clipped = summary if len(summary) <= cap else "…" + summary[-cap:]
        if take(clipped):
            ctx.summary = clipped

    # 2. Facts the current interlocutor witnessed or learned — prevents contradictions.
    if npc_id and npc_id in state.npcs:
        for fact_id in reversed(state.npcs[npc_id].memories):
            fact = state.facts.get(fact_id)
            if fact and take(tr(fact.text, lang)):
                ctx.npc_memories.append(tr(fact.text, lang))

    # 3. Recent turns, newest first, with narration excerpts.
    for turn in reversed(recent):
        excerpt = turn.narration if len(turn.narration) <= 420 else turn.narration[:420] + "…"
        line = f"{turn.player_input} → {excerpt}"
        if not take(line):
            break
        ctx.recent.insert(0, RecentTurn(turn.number, turn.player_input, excerpt))

    # 4. Long-term facts ranked by relevance.
    words = {w for w in normalize(player_input).split() if len(w) > 3}
    ranked = sorted(
        state.facts.values(),
        key=lambda f: score_fact(f, scene_ids, words, state.turn),
        reverse=True,
    )
    already = set(ctx.npc_memories)
    for fact in ranked:
        text = tr(fact.text, lang)
        if text in already:
            continue
        if take(text):
            ctx.facts.append(text)
        else:
            ctx.dropped_facts += 1

    ctx.used_chars = budget_chars - remaining
    return ctx
