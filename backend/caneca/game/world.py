"""Loads the YAML content, merges the files and validates every cross-reference."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from caneca.game.content_schema import (
    Ability,
    Achievement,
    Chapter,
    Condition,
    ContentFile,
    Effect,
    Ending,
    Interaction,
    Item,
    Location,
    Npc,
    Quest,
    RandomEvent,
    Recipe,
    Region,
    WorldMeta,
)

CONTENT_DIR = Path(__file__).parent / "content"


class ContentError(ValueError):
    """Raised when the authored content is inconsistent."""


@dataclass
class World:
    meta: WorldMeta
    regions: dict[str, Region] = field(default_factory=dict)
    chapters: dict[int, Chapter] = field(default_factory=dict)
    locations: dict[str, Location] = field(default_factory=dict)
    items: dict[str, Item] = field(default_factory=dict)
    npcs: dict[str, Npc] = field(default_factory=dict)
    interactions: list[Interaction] = field(default_factory=list)
    recipes: list[Recipe] = field(default_factory=list)
    quests: dict[str, Quest] = field(default_factory=dict)
    abilities: dict[str, Ability] = field(default_factory=dict)
    events: list[RandomEvent] = field(default_factory=list)
    achievements: dict[str, Achievement] = field(default_factory=dict)
    endings: dict[str, Ending] = field(default_factory=dict)

    def feature_owner(self, feature_id: str) -> Location | None:
        for loc in self.locations.values():
            if any(f.id == feature_id for f in loc.features):
                return loc
        return None


def _put(registry: dict[str, object], key: str, value: object, kind: str) -> None:
    if key in registry:
        raise ContentError(f"{kind} duplicado: {key}")
    registry[key] = value


def merge(files: Iterable[ContentFile]) -> World:
    meta: WorldMeta | None = None
    world_parts: dict[str, dict[str, object]] = {
        k: {}
        for k in (
            "regions",
            "locations",
            "items",
            "npcs",
            "quests",
            "abilities",
            "achievements",
            "endings",
        )
    }
    chapters: dict[int, Chapter] = {}
    interactions: list[Interaction] = []
    recipes: list[Recipe] = []
    events: list[RandomEvent] = []
    for f in files:
        if f.meta:
            if meta:
                raise ContentError("meta definido em mais de um arquivo")
            meta = f.meta
        for kind in world_parts:
            for obj in getattr(f, kind):
                _put(world_parts[kind], obj.id, obj, kind)
        for ch in f.chapters:
            if ch.number in chapters:
                raise ContentError(f"capítulo duplicado: {ch.number}")
            chapters[ch.number] = ch
        interactions.extend(f.interactions)
        recipes.extend(f.recipes)
        events.extend(f.events)
    if meta is None:
        raise ContentError("nenhum arquivo define meta")
    world = World(
        meta=meta,
        chapters=chapters,
        interactions=interactions,
        recipes=recipes,
        events=events,
        **world_parts,  # type: ignore[arg-type]
    )
    validate(world)
    return world


def _walk_conditions(conds: Iterable[Condition]) -> Iterable[Condition]:
    for c in conds:
        yield c
        yield from _walk_conditions(c.any or [])
        yield from _walk_conditions(c.all or [])
        if c.not_:
            yield from _walk_conditions([c.not_])


def validate(w: World) -> None:
    errors: list[str] = []
    feature_ids = {f.id for loc in w.locations.values() for f in loc.features}
    entity_ids = set(w.items) | set(w.npcs) | feature_ids | set(w.abilities) | {"self"}

    def need(kind: str, ref: str | None, pool: Iterable[str], where: str) -> None:
        if ref is not None and ref not in pool:
            errors.append(f"{where}: {kind} inexistente '{ref}'")

    def check_conditions(conds: Iterable[Condition], where: str) -> None:
        for c in _walk_conditions(conds):
            need("item", c.has_item, w.items, where)
            need("item", c.lacks_item, w.items, where)
            if c.item_at:
                need("item", c.item_at[0], w.items, where)
            for loc in [c.at] if isinstance(c.at, str) else (c.at or []):
                need("local", loc, w.locations, where)
            need("local", c.visited, w.locations, where)
            need("npc", c.rel, w.npcs, where)
            need("npc", c.met, w.npcs, where)
            if c.npc_at:
                need("npc", c.npc_at[0], w.npcs, where)
                need("local", c.npc_at[1], w.locations, where)
            if c.npc_remembers:
                need("npc", c.npc_remembers[0], w.npcs, where)
            need("missão", c.quest, w.quests, where)
            need("habilidade", c.ability, w.abilities, where)
            if c.objective:
                q, _, o = c.objective.partition(".")
                need("missão", q, w.quests, where)
                if q in w.quests and o not in {ob.id for ob in w.quests[q].objectives}:
                    errors.append(f"{where}: objetivo inexistente '{c.objective}'")

    def check_effects(effects: Iterable[Effect], where: str) -> None:
        for e in effects:
            check_conditions(e.when, where)
            for ref in (e.give_item, e.take_item):
                need("item", ref, w.items, where)
            if e.place_item:
                need("item", e.place_item[0], w.items, where)
                if e.place_item[1] != "void":
                    need("local", e.place_item[1], w.locations, where)
            for npc in e.rel or {}:
                need("npc", npc, w.npcs, where)
            for npc in e.npc_mood or {}:
                need("npc", npc, w.npcs, where)
            for npc in e.npc_remembers or {}:
                need("npc", npc, w.npcs, where)
            for npc, loc in (e.move_npc or {}).items():
                need("npc", npc, w.npcs, where)
                if loc != "void":
                    need("local", loc, w.locations, where)
            need("local", e.move_player, w.locations, where)
            for ex in [e.unlock_exit] if isinstance(e.unlock_exit, str) else (e.unlock_exit or []):
                a, _, b = ex.partition(">")
                need("local", a, w.locations, where)
                need("local", b, w.locations, where)
            need("missão", e.quest_start, w.quests, where)
            need("missão", e.quest_fail, w.quests, where)
            if e.quest_complete:
                need("missão", e.quest_complete.id, w.quests, where)
                q = w.quests.get(e.quest_complete.id)
                if q and e.quest_complete.outcome and e.quest_complete.outcome not in q.outcomes:
                    errors.append(f"{where}: desfecho inexistente '{e.quest_complete.outcome}'")
            if e.objective:
                q_id, _, o = e.objective.partition(".")
                need("missão", q_id, w.quests, where)
                if q_id in w.quests and o not in {ob.id for ob in w.quests[q_id].objectives}:
                    errors.append(f"{where}: objetivo inexistente '{e.objective}'")
            need("habilidade", e.learn, w.abilities, where)
            need("conquista", e.achievement, w.achievements, where)
            need("final", e.ending, w.endings, where)
            if e.chapter is not None and e.chapter not in w.chapters:
                errors.append(f"{where}: capítulo inexistente {e.chapter}")
            if e.discover is not None and e.discover not in entity_ids | set(w.locations):
                errors.append(f"{where}: descoberta inexistente '{e.discover}'")

    need("local", w.meta.start_location, w.locations, "meta")
    for q in w.meta.initial_quests:
        need("missão", q, w.quests, "meta")
    for ch in w.chapters.values():
        need("região", ch.region, w.regions, f"capítulo {ch.number}")

    for loc in w.locations.values():
        where = f"local {loc.id}"
        need("região", loc.region, w.regions, where)
        for v in loc.views:
            need("local", v, w.locations, where)
        targets = [ex.to for ex in loc.exits]
        if len(targets) != len(set(targets)):
            errors.append(f"{where}: saídas duplicadas para o mesmo destino")
        for ex in loc.exits:
            need("local", ex.to, w.locations, where)
            check_conditions(ex.conditions + ex.visible_if, where)
            check_effects(ex.fail_effects, where)
        for feat in loc.features:
            check_conditions(feat.visible_if, f"{where}/{feat.id}")
        check_effects(loc.on_enter, where)

    for item in w.items.values():
        valid_initial = {*w.locations, *w.npcs, "inventory"}
        if item.initial and item.initial not in valid_initial:
            errors.append(f"item {item.id}: posição inicial inválida '{item.initial}'")

    for npc in w.npcs.values():
        where = f"npc {npc.id}"
        need("local", npc.location, w.locations, where)
        for ref in npc.likes + npc.dislikes:
            need("item", ref, w.items, where)
        for g in npc.greetings:
            check_conditions(g.conditions, where)
        for t in npc.topics:
            check_conditions(t.conditions, f"{where}/{t.id}")
            check_effects(t.effects, f"{where}/{t.id}")
        for s in npc.secrets:
            check_conditions(s.reveal_if, f"{where}/{s.id}")
        if not npc.greetings:
            errors.append(f"{where}: precisa de ao menos uma saudação")

    seen_inter: set[str] = set()
    for it in w.interactions:
        where = f"interação {it.id}"
        if it.id in seen_inter:
            errors.append(f"{where}: id duplicado")
        seen_inter.add(it.id)
        if it.target and it.target not in entity_ids and not it.target.startswith("exit:"):
            errors.append(f"{where}: alvo inexistente '{it.target}'")
        need("item", it.item, w.items, where)
        for at_id in [it.at] if isinstance(it.at, str) else (it.at or []):
            need("local", at_id, w.locations, where)
        check_conditions(it.conditions, where)
        check_effects(it.effects + it.fail_effects, where)

    for r in w.recipes:
        for ref in (*r.inputs, r.output):
            need("item", ref, w.items, f"receita {r.id}")
        check_effects(r.effects, f"receita {r.id}")

    for quest in w.quests.values():
        check_effects(quest.rewards, f"missão {quest.id}")
        need("npc", quest.giver, w.npcs, f"missão {quest.id}")
    for a in w.abilities.values():
        check_effects(a.effects, f"habilidade {a.id}")
    for ev in w.events:
        for r_id in ev.regions:
            need("região", r_id, w.regions, f"evento {ev.id}")
        check_conditions(ev.conditions, f"evento {ev.id}")
        check_effects(ev.effects, f"evento {ev.id}")

    if errors:
        raise ContentError("conteúdo inválido:\n  " + "\n  ".join(errors))


def load_files(directory: Path = CONTENT_DIR) -> list[ContentFile]:
    files: list[ContentFile] = []
    for path in sorted(directory.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        try:
            files.append(ContentFile.model_validate(raw))
        except ValueError as exc:
            raise ContentError(f"{path.name}: {exc}") from exc
    return files


@lru_cache(maxsize=1)
def get_world() -> World:
    return merge(load_files())
