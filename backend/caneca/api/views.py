"""Read models sent to the UI. They expose only what the player is allowed to know."""

from __future__ import annotations

from typing import Any

from caneca.ai.prompts import clock_text, relationship_label
from caneca.game.engine import Engine, Suggestion
from caneca.game.i18n import tr
from caneca.game.mechanics import GameEvent, all_hold
from caneca.game.messages import STATUS_NAMES
from caneca.game.rules import DIFFICULTY, xp_for_level
from caneca.game.state import INVENTORY, WorldState


def game_view(engine: Engine, state: WorldState, lang: str, meta: dict[str, Any]) -> dict[str, Any]:
    w = engine.world
    loc = w.locations[state.location]
    region = w.regions[loc.region]
    chapter = w.chapters.get(state.chapter)
    st = state.stats
    carried = sum(w.items[i].weight for i in state.inventory())
    capacity = DIFFICULTY[state.settings.difficulty].capacity

    present = engine.present_npcs(state)
    remote = engine.remote_npcs(state)
    location = {
        "id": loc.id,
        "name": tr(loc.name, lang),
        "short": tr(loc.short, lang),
        "description": tr(loc.description, lang),
        "region": loc.region,
        "dark": loc.dark,
        "heat": loc.heat is not None,
        "ambient_temp": loc.ambient_temp,
        "features": [{"id": f.id, "name": tr(f.name, lang)} for f in engine.visible_features(state)],
        "items": [
            {"id": i, "name": tr(w.items[i].name, lang), "icon": w.items[i].icon}
            for i in state.items_at(state.location)
        ],
        "npcs": [
            {
                "id": n,
                "name": tr(w.npcs[n].name, lang),
                "kind": tr(w.npcs[n].kind, lang),
                "icon": w.npcs[n].icon,
                "remote": n in remote and n not in present,
                "mood": state.npcs[n].mood,
            }
            for n in present + [r for r in remote if r not in present]
        ],
        "exits": [
            {
                "to": ex.to,
                "label": tr(ex.label, lang),
                "kind": ex.kind,
                "allowed": engine.exit_allowed(state, loc, ex),
                "visited": ex.to in state.visited,
            }
            for ex in engine.visible_exits(state)
        ],
    }

    abilities = []
    for ab_id in state.abilities:
        ab = w.abilities[ab_id]
        abilities.append(
            {
                "id": ab_id,
                "name": tr(ab.name, lang),
                "description": tr(ab.description, lang),
                "kind": ab.kind,
                "cooldown": state.cooldowns.get(ab_id, 0),
                "cost_energy": ab.cost_energy,
                "cost_coffee": ab.cost_coffee,
            }
        )

    quests: list[dict[str, Any]] = []
    for q_id, qs in state.quests.items():
        if qs.status == "inactive":
            continue
        q = w.quests[q_id]
        quests.append(
            {
                "id": q_id,
                "kind": q.kind,
                "name": tr(q.name, lang),
                "description": tr(q.description, lang),
                "status": qs.status,
                "outcome": tr(q.outcomes[qs.outcome], lang) if qs.outcome in q.outcomes else None,
                "objectives": [
                    {"id": o.id, "text": tr(o.text, lang), "done": o.id in qs.done, "optional": o.optional}
                    for o in q.objectives
                ],
                "started_turn": qs.started_turn,
            }
        )
    quests.sort(
        key=lambda q: ({"active": 0, "completed": 1, "failed": 2}[q["status"]], {"main": 0}.get(q["kind"], 1))
    )

    relationships = [
        {
            "id": n_id,
            "name": tr(w.npcs[n_id].name, lang),
            "kind": tr(w.npcs[n_id].kind, lang),
            "icon": w.npcs[n_id].icon,
            "value": ns.relationship,
            "label": relationship_label(ns.relationship, lang),
            "mood": ns.mood,
            "location": tr(w.locations[ns.location].name, lang) if ns.location in w.locations else "",
            "companion": f"companion:{n_id}" in state.flags,
            "memories": len(ns.memories),
        }
        for n_id, ns in state.npcs.items()
        if ns.met
    ]

    known_locations = set(state.visited) | {d for d in state.discovered if d in w.locations}
    nodes = [
        {
            "id": l_id,
            "name": tr(w.locations[l_id].name, lang),
            "region": w.locations[l_id].region,
            "x": w.locations[l_id].map_pos[0],
            "y": w.locations[l_id].map_pos[1],
            "visited": l_id in state.visited,
            "current": l_id == state.location,
        }
        for l_id in w.locations
        if l_id in known_locations
    ]
    edges = sorted(
        {
            tuple(sorted((l_id, ex.to)))
            for l_id in state.visited
            for ex in w.locations[l_id].exits
            if ex.to in known_locations and all_hold(ex.visible_if, w, state)
        }
    )
    regions = [
        {
            "id": r.id,
            "name": tr(r.name, lang),
            "chapter": r.chapter,
            "palette": r.palette,
            "known": any(n["region"] == r.id for n in nodes),
        }
        for r in sorted(w.regions.values(), key=lambda r: r.chapter)
    ]

    achievements = [
        {
            "id": a.id,
            "unlocked": a.id in state.achievements,
            "name": tr(a.name, lang) if (a.id in state.achievements or not a.secret) else "???",
            "description": tr(a.description, lang) if (a.id in state.achievements or not a.secret) else "",
        }
        for a in w.achievements.values()
    ]

    codex = []
    for ent in state.discovered:
        if ent in w.npcs:
            codex.append(
                {
                    "id": ent,
                    "kind": "npc",
                    "name": tr(w.npcs[ent].name, lang),
                    "description": tr(w.npcs[ent].description, lang),
                }
            )
        elif ent in w.items:
            codex.append(
                {
                    "id": ent,
                    "kind": "item",
                    "name": tr(w.items[ent].name, lang),
                    "description": tr(w.items[ent].description, lang),
                }
            )
        elif ent in w.locations:
            codex.append(
                {
                    "id": ent,
                    "kind": "location",
                    "name": tr(w.locations[ent].name, lang),
                    "description": tr(w.locations[ent].description, lang),
                }
            )
        else:
            owner = w.feature_owner(ent)
            if owner:
                feat = next(f for f in owner.features if f.id == ent)
                codex.append(
                    {
                        "id": ent,
                        "kind": "feature",
                        "name": tr(feat.name, lang),
                        "description": tr(feat.description, lang),
                    }
                )

    ending = None
    if state.ending:
        e = w.endings[state.ending]
        ending = {"id": e.id, "name": tr(e.name, lang), "text": tr(e.text, lang), "kind": e.kind}

    return {
        **meta,
        "turn": state.turn,
        "language": state.settings.language,
        "settings": state.settings.model_dump(),
        "mug": state.mug.model_dump(),
        "chapter": {"number": state.chapter, "title": tr(chapter.title, lang) if chapter else ""},
        "region": {"id": region.id, "name": tr(region.name, lang), "palette": region.palette},
        "clock": clock_text(state),
        "stats": {
            "temperature": round(st.temperature, 1),
            "coffee": round(st.coffee, 1),
            "integrity": round(st.integrity, 1),
            "energy": round(st.energy, 1),
            "courage": round(st.courage),
            "creativity": round(st.creativity),
            "xp": st.xp,
            "level": st.level,
            "xp_level_start": xp_for_level(st.level),
            "xp_next": xp_for_level(st.level + 1),
        },
        "statuses": [
            {"id": s, "label": tr(STATUS_NAMES.get(s, {"pt-BR": s, "en": s}), lang)} for s in state.statuses
        ],
        "abilities": abilities,
        "location": location,
        "inventory": [
            {
                "id": i,
                "name": tr(w.items[i].name, lang),
                "description": tr(w.items[i].description, lang),
                "icon": w.items[i].icon,
                "weight": w.items[i].weight,
            }
            for i in state.inventory()
        ],
        "capacity": {"used": carried, "max": capacity},
        "quests": quests,
        "relationships": relationships,
        "map": {"regions": regions, "nodes": nodes, "edges": [list(e) for e in edges]},
        "achievements": achievements,
        "codex": codex,
        "suggestions": [s.as_dict(lang) for s in engine.suggestions(state)],
        "ending": ending,
        "defeated": state.defeated,
    }


def suggestion_dicts(items: list[Suggestion], lang: str) -> list[dict[str, Any]]:
    return [s.as_dict(lang) for s in items]


def event_view(engine: Engine, ev: GameEvent | dict[str, Any], lang: str) -> dict[str, Any] | None:
    """A compact, localized description of a structured event, for toasts and history."""
    w = engine.world
    kind = ev.kind if isinstance(ev, GameEvent) else ev["kind"]
    d = ev.data if isinstance(ev, GameEvent) else ev["data"]
    text = ev.text if isinstance(ev, GameEvent) else ev.get("text")
    label: str | None = None
    if kind == "stat":
        if d["reason"] in ("ambient", "effort") and abs(d["delta"]) < 3:
            return None
        return {"kind": kind, "stat": d["stat"], "delta": d["delta"], "value": d["value"]}
    if kind in ("item_gained", "item_lost"):
        label = tr(w.items[d["item"]].name, lang)
    elif kind == "relationship":
        label = tr(w.npcs[d["npc"]].name, lang)
    elif kind == "moved":
        label = tr(w.locations[d["to"]].name, lang)
    elif kind in (
        "quest_started",
        "quest_completed",
        "quest_failed",
        "objective",
        "achievement",
        "level_up",
        "ability_learned",
        "random_event",
        "ending",
        "defeat",
    ):
        label = tr(text, lang) if text else None
    elif kind == "xp":
        return {"kind": kind, "amount": d["amount"]}
    elif kind == "check":
        return {"kind": kind, **d}
    elif kind == "chapter":
        ch = w.chapters[d["chapter"]]
        label = tr(ch.title, lang)
    elif kind == "npc_moved":
        return None
    else:
        return None
    return {
        "kind": kind,
        "label": label,
        **{k: v for k, v in d.items() if isinstance(v, int | float | str | bool)},
    }


def inventory_names(engine: Engine, state: WorldState, lang: str) -> list[str]:
    return [
        tr(engine.world.items[i].name, lang)
        for i, where in state.item_locations.items()
        if where == INVENTORY
    ]
