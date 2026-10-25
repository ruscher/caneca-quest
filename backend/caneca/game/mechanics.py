"""Condition evaluation and effect application — the only code that mutates WorldState.

``Mutator`` collects structured events while it changes the state, so the narrator,
the journal and the UI all learn about consequences from the same source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from caneca.game.content_schema import Condition, Effect, Location
from caneca.game.i18n import fmt
from caneca.game.messages import M
from caneca.game.rules import (
    BALANCE,
    DERIVED_STATUSES,
    DIFFICULTY,
    clamp_stat,
    damage_amount,
    derive_statuses,
    level_for_xp,
)
from caneca.game.state import INVENTORY, VOID, Fact, NpcState, WorldState
from caneca.game.world import World


def location_npcs(world: World, state: WorldState, location_id: str) -> list[str]:
    return [n for n, s in state.npcs.items() if s.location == location_id]


def evaluate(cond: Condition, world: World, state: WorldState) -> bool:
    s = state
    checks: list[bool] = []
    if cond.flag is not None:
        checks.append(cond.flag in s.flags)
    if cond.not_flag is not None:
        checks.append(cond.not_flag not in s.flags)
    if cond.has_item is not None:
        checks.append(s.item_locations.get(cond.has_item) == INVENTORY)
    if cond.lacks_item is not None:
        checks.append(s.item_locations.get(cond.lacks_item) != INVENTORY)
    if cond.item_at is not None:
        checks.append(s.item_locations.get(cond.item_at[0]) == cond.item_at[1])
    if cond.at is not None:
        allowed = [cond.at] if isinstance(cond.at, str) else cond.at
        checks.append(s.location in allowed)
    if cond.visited is not None:
        checks.append(cond.visited in s.visited)
    if cond.stat is not None:
        checks.append(_threshold(getattr(s.stats, cond.stat), cond))
    if cond.rel is not None:
        npc = s.npcs.get(cond.rel)
        checks.append(npc is not None and _threshold(npc.relationship, cond))
    if cond.counter is not None:
        checks.append(_threshold(s.counters.get(cond.counter, 0), cond))
    if cond.npc_at is not None:
        npc = s.npcs.get(cond.npc_at[0])
        checks.append(npc is not None and npc.location == cond.npc_at[1])
    if cond.met is not None:
        npc = s.npcs.get(cond.met)
        checks.append(npc is not None and npc.met)
    if cond.npc_remembers is not None:
        npc = s.npcs.get(cond.npc_remembers[0])
        checks.append(npc is not None and cond.npc_remembers[1] in npc.memories)
    if cond.quest is not None:
        q = s.quests.get(cond.quest)
        status = q.status if q else "inactive"
        checks.append(status == (cond.status or "active"))
    if cond.objective is not None:
        q_id, _, o_id = cond.objective.partition(".")
        q = s.quests.get(q_id)
        checks.append(q is not None and o_id in q.done)
    if cond.ability is not None:
        checks.append(cond.ability in s.abilities)
    if cond.level_gte is not None:
        checks.append(s.stats.level >= cond.level_gte)
    if cond.has_status is not None:
        checks.append(cond.has_status in s.statuses)
    if cond.lacks_status is not None:
        checks.append(cond.lacks_status not in s.statuses)
    if cond.difficulty is not None:
        checks.append(s.settings.difficulty == cond.difficulty)
    if cond.chapter_gte is not None:
        checks.append(s.chapter >= cond.chapter_gte)
    if cond.any is not None:
        checks.append(any(evaluate(c, world, s) for c in cond.any))
    if cond.all is not None:
        checks.append(all(evaluate(c, world, s) for c in cond.all))
    if cond.not_ is not None:
        checks.append(not evaluate(cond.not_, world, s))
    return all(checks)


def _threshold(value: float, cond: Condition) -> bool:
    if cond.gte is not None and value < cond.gte:
        return False
    return not (cond.lte is not None and value > cond.lte)


def all_hold(conds: list[Condition], world: World, state: WorldState) -> bool:
    return all(evaluate(c, world, state) for c in conds)


@dataclass
class GameEvent:
    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    text: dict[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "data": self.data, "text": self.text}


class Mutator:
    """Applies effects to a state, recording every consequence as a ``GameEvent``."""

    def __init__(self, world: World, state: WorldState) -> None:
        self.world = world
        self.state = state
        self.events: list[GameEvent] = []
        self.messages: list[dict[str, str]] = []
        self.player_input: str = ""

    # -- helpers ---------------------------------------------------------------
    def emit(self, kind: str, text: dict[str, str] | None = None, **data: Any) -> None:
        self.events.append(GameEvent(kind, data, text))
        if text:
            self.messages.append(text)

    def say(self, text: dict[str, str]) -> None:
        self.messages.append(text)

    def present_npcs(self) -> list[str]:
        return location_npcs(self.world, self.state, self.state.location)

    # -- stats -----------------------------------------------------------------
    def change_stat(self, name: str, delta: float, reason: str = "") -> float:
        if delta == 0:
            return 0.0
        stats = self.state.stats
        before = float(getattr(stats, name))
        after = clamp_stat(name, before + delta)
        if name == "integrity" and after < before:
            floor = DIFFICULTY[self.state.settings.difficulty].min_integrity
            if after < floor:
                after = floor
                self.say(M["story_protect"])
        setattr(stats, name, after)
        real = round(after - before, 2)
        if real:
            self.emit("stat", None, stat=name, delta=real, value=after, reason=reason)
        return real

    def set_stat(self, name: str, value: float) -> None:
        current = float(getattr(self.state.stats, name))
        self.change_stat(name, value - current, "set")

    def add_xp(self, amount: int) -> None:
        if amount <= 0:
            return
        if "curious" in self.state.mug.traits:
            amount = round(amount * 1.1)
        stats = self.state.stats
        stats.xp += amount
        self.emit("xp", None, amount=amount, total=stats.xp)
        new_level = level_for_xp(stats.xp)
        while stats.level < new_level:
            stats.level += 1
            stats.energy = 100.0
            stats.courage = clamp_stat("courage", stats.courage + 5)
            stats.creativity = clamp_stat("creativity", stats.creativity + 5)
            self.emit("level_up", fmt(M["level_up"], level=stats.level), level=stats.level)
            for ability in self.world.abilities.values():
                if ability.auto_at_level == stats.level:
                    self.learn(ability.id)

    def learn(self, ability_id: str) -> None:
        if ability_id in self.state.abilities:
            return
        ability = self.world.abilities[ability_id]
        self.state.abilities.append(ability_id)
        self.emit("ability_learned", fmt(M["learned"], ability=ability.name), ability=ability_id)

    # -- items -----------------------------------------------------------------
    def move_item(self, item_id: str, where: str) -> None:
        before = self.state.item_locations.get(item_id, VOID)
        if before == where:
            return
        self.state.item_locations[item_id] = where
        if where == INVENTORY:
            self.emit("item_gained", None, item=item_id, origin=before)
            self.discover(item_id)
        elif before == INVENTORY:
            self.emit("item_lost", None, item=item_id, destination=where)

    def discover(self, entity_id: str) -> None:
        if entity_id in self.state.discovered:
            return
        self.state.discovered.append(entity_id)
        self.emit("discovered", None, entity=entity_id)

    # -- npcs ------------------------------------------------------------------
    def npc(self, npc_id: str) -> NpcState:
        return self.state.npcs[npc_id]

    def change_rel(self, npc_id: str, delta: int) -> None:
        npc = self.npc(npc_id)
        if "charming" in self.state.mug.traits and delta > 0:
            delta = round(delta * 1.2)
        before = npc.relationship
        npc.relationship = max(-100, min(100, before + delta))
        if npc.relationship != before:
            self.emit(
                "relationship", None, npc=npc_id, delta=npc.relationship - before, value=npc.relationship
            )

    def meet(self, npc_id: str) -> None:
        npc = self.npc(npc_id)
        if not npc.met:
            npc.met = True
            self.discover(npc_id)
            self.emit("met", None, npc=npc_id)

    # -- quests ----------------------------------------------------------------
    def start_quest(self, quest_id: str) -> None:
        q = self.state.quest(quest_id)
        if q.status != "inactive":
            return
        q.status = "active"
        q.started_turn = self.state.turn
        quest = self.world.quests[quest_id]
        self.emit("quest_started", fmt(M["quest_started"], quest=quest.name), quest=quest_id)
        self.journal_auto("quest", quest.name, quest.description)

    def complete_objective(self, ref: str) -> None:
        q_id, _, o_id = ref.partition(".")
        quest = self.world.quests[q_id]
        q = self.state.quest(q_id)
        if q.status == "inactive":
            self.start_quest(q_id)
        if q.status != "active" or o_id in q.done:
            return
        q.done.append(o_id)
        objective = next(o for o in quest.objectives if o.id == o_id)
        self.emit("objective", fmt(M["objective_done"], objective=objective.text), quest=q_id, objective=o_id)
        required = [o.id for o in quest.objectives if not o.optional]
        if quest.auto_complete and all(o in q.done for o in required):
            self.complete_quest(q_id, None)

    def complete_quest(self, quest_id: str, outcome: str | None) -> None:
        quest = self.world.quests[quest_id]
        q = self.state.quest(quest_id)
        if q.status in ("completed", "failed"):
            return
        if q.status == "inactive":
            self.start_quest(quest_id)
        q.status = "completed"
        q.outcome = outcome
        q.finished_turn = self.state.turn
        self.emit(
            "quest_completed", fmt(M["quest_completed"], quest=quest.name), quest=quest_id, outcome=outcome
        )
        text = quest.outcomes.get(outcome, quest.description) if outcome else quest.description
        self.journal_auto("quest_done", quest.name, text)
        self.add_xp(quest.xp)
        self.apply_all(quest.rewards)

    def fail_quest(self, quest_id: str) -> None:
        q = self.state.quest(quest_id)
        if q.status in ("completed", "failed"):
            return
        q.status = "failed"
        q.finished_turn = self.state.turn
        quest = self.world.quests[quest_id]
        self.emit("quest_failed", fmt(M["quest_failed"], quest=quest.name), quest=quest_id)

    # -- memory ----------------------------------------------------------------
    def journal_auto(self, kind: str, title: dict[str, str], text: dict[str, str]) -> None:
        self.emit(
            "journal",
            None,
            entry_kind=kind,
            title=title,
            body=text,
            location=self.state.location,
            participants=self.present_npcs(),
            decision=self.player_input,
        )

    def add_fact(
        self, fact_id: str, text: dict[str, str], importance: int, tags: list[str], witnesses: str
    ) -> None:
        if fact_id not in self.state.facts:
            self.state.facts[fact_id] = Fact(
                id=fact_id,
                text=text,
                turn=self.state.turn,
                importance=importance,
                location=self.state.location,
                tags=tags,
            )
            self.emit("fact", None, fact=fact_id)
        if witnesses == "present":
            for npc_id in self.present_npcs():
                self.remember(npc_id, fact_id)

    def remember(self, npc_id: str, fact_id: str) -> None:
        npc = self.npc(npc_id)
        if fact_id not in npc.memories:
            npc.memories.append(fact_id)

    # -- effect dispatch -------------------------------------------------------
    def apply_all(self, effects: list[Effect]) -> None:
        for effect in effects:
            self.apply(effect)

    def apply(self, e: Effect) -> None:
        s = self.state
        if e.when and not all_hold(e.when, self.world, s):
            return
        for flag in _as_list(e.set_flag):
            if flag not in s.flags:
                s.flags.append(flag)
        for flag in _as_list(e.clear_flag):
            if flag in s.flags:
                s.flags.remove(flag)
        if e.give_item:
            self.move_item(e.give_item, INVENTORY)
        if e.take_item:
            self.move_item(e.take_item, VOID)
        if e.place_item:
            self.move_item(e.place_item[0], e.place_item[1])
        for name, delta in (e.stats or {}).items():
            if name == "integrity" and delta < 0:
                delta = -damage_amount(s, -delta)
            self.change_stat(name, delta, "effect")
        for name, value in (e.set_stats or {}).items():
            self.set_stat(name, value)
        for npc_id, delta in (e.rel or {}).items():
            self.change_rel(npc_id, delta)
        for npc_id, mood in (e.npc_mood or {}).items():
            self.npc(npc_id).mood = mood
        for npc_id, fact_id in (e.npc_remembers or {}).items():
            self.remember(npc_id, fact_id)
        for npc_id, loc in (e.move_npc or {}).items():
            if self.npc(npc_id).location != loc:
                self.npc(npc_id).location = loc
                self.emit("npc_moved", None, npc=npc_id, to=loc)
        for exit_ref in _as_list(e.unlock_exit):
            if exit_ref not in s.unlocked_exits:
                s.unlocked_exits.append(exit_ref)
                self.emit("exit_unlocked", None, exit=exit_ref)
        if e.quest_start:
            self.start_quest(e.quest_start)
        if e.objective:
            self.complete_objective(e.objective)
        if e.quest_complete:
            self.complete_quest(e.quest_complete.id, e.quest_complete.outcome)
        if e.quest_fail:
            self.fail_quest(e.quest_fail)
        if e.learn:
            self.learn(e.learn)
        if e.journal:
            self.journal_auto("story", e.journal.title, e.journal.text)
        if e.fact:
            f = e.fact
            self.add_fact(f.id, f.text, f.importance, f.tags, f.witnesses)
        if e.achievement and e.achievement not in s.achievements:
            s.achievements.append(e.achievement)
            ach = self.world.achievements[e.achievement]
            self.emit("achievement", fmt(M["achievement"], name=ach.name), id=e.achievement)
        if e.discover:
            self.discover(e.discover)
        for faction, delta in (e.reputation or {}).items():
            s.reputation[faction] = s.reputation.get(faction, 0) + delta
            self.emit("reputation", None, faction=faction, delta=delta)
        for counter, step in (e.counter or {}).items():
            s.counters[counter] = s.counters.get(counter, 0) + step
        if e.status_add and e.status_add not in s.statuses:
            s.statuses.append(e.status_add)
            self.emit("status", None, status=e.status_add, added=True)
        if e.status_remove and e.status_remove in s.statuses:
            s.statuses.remove(e.status_remove)
            self.emit("status", None, status=e.status_remove, added=False)
        if e.minutes:
            s.minutes += e.minutes
        if e.xp:
            self.add_xp(e.xp)
        if e.chapter is not None and e.chapter > s.chapter:
            s.chapter = e.chapter
            chapter = self.world.chapters[e.chapter]
            self.emit("chapter", None, chapter=e.chapter)
            self.journal_auto("chapter", chapter.title, self.world.regions[chapter.region].name)
        if e.move_player:
            self.enter_location(e.move_player)
        if e.ending and not s.ending:
            s.ending = e.ending
            ending = self.world.endings[e.ending]
            self.emit("ending", ending.text, ending=e.ending)
            self.journal_auto("ending", ending.name, ending.text)

    def enter_location(self, loc_id: str) -> None:
        s = self.state
        if s.location == loc_id:
            return
        origin = s.location
        s.location = loc_id
        if "hidden" in s.statuses:
            s.statuses.remove("hidden")
        loc: Location = self.world.locations[loc_id]
        first = loc_id not in s.visited
        self.emit("moved", None, origin=origin, to=loc_id, first=first)
        for npc_id, npc in s.npcs.items():
            if f"companion:{npc_id}" in s.flags and npc.location == origin:
                npc.location = loc_id
                self.emit("npc_moved", None, npc=npc_id, to=loc_id, companion=True)
        if first:
            s.visited.append(loc_id)
            self.discover(loc_id)
            self.add_xp(BALANCE.xp_per_new_location)
        self.apply_all(loc.on_enter)

    def refresh_statuses(self) -> None:
        narrative = [st for st in self.state.statuses if st not in DERIVED_STATUSES]
        derived = derive_statuses(self.state.stats)
        self.state.statuses = narrative + derived


def _as_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)
