"""Deterministic action resolution — the single source of truth of the game world.

``Engine.resolve`` takes the current state and a validated intent and returns a new
state plus a structured ``TurnOutcome``. It never reads AI output: the narrator only
describes what the engine already decided.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from caneca.game.content_schema import Check, Exit, Interaction, Location, Npc
from caneca.game.i18n import fmt, join, lt, tr
from caneca.game.mechanics import GameEvent, Mutator, all_hold, location_npcs
from caneca.game.messages import (
    DRINK_NAMES,
    MATERIAL_NAMES,
    STYLE_NAMES,
    M,
)
from caneca.game.parser import SELF_KEYWORDS, Candidate, Intent, normalize, parse
from caneca.game.rules import (
    BALANCE,
    DIFFICULTY,
    CheckResult,
    cool,
    cooling_multiplier,
    damage_amount,
    energy_cost,
    initial_stats,
    make_rng,
    roll_check,
)
from caneca.game.state import (
    INVENTORY,
    AdventureSettings,
    MugIdentity,
    NpcState,
    QuestState,
    WorldState,
)
from caneca.game.world import World

META_VERBS = {"inventory", "status", "help"}


@dataclass
class Suggestion:
    label: dict[str, str]
    verb: str
    target: str | None = None
    item: str | None = None
    kind: str = "action"
    interaction: str | None = None

    def as_dict(self, lang: str) -> dict[str, Any]:
        return {
            "label": tr(self.label, lang),
            "verb": self.verb,
            "target": self.target,
            "item": self.item,
            "kind": self.kind,
            "interaction": self.interaction,
        }


@dataclass
class TurnOutcome:
    intent: Intent
    state: WorldState
    messages: list[dict[str, str]]
    events: list[GameEvent]
    check: CheckResult | None = None
    success: bool | None = None
    minutes: int = 0
    meta: bool = False
    dialogue_npc: str | None = None
    topic: str | None = None
    suggestions: list[Suggestion] = field(default_factory=list)

    def narration(self, lang: str) -> str:
        return "\n\n".join(tr(m, lang) for m in self.messages if tr(m, lang))


@dataclass
class _Ctx:
    mut: Mutator
    intent: Intent
    rng: random.Random
    check: CheckResult | None = None
    success: bool | None = None
    minutes: int = 3
    energy: float = 1.0
    meta: bool = False
    dialogue_npc: str | None = None
    topic: str | None = None

    @property
    def s(self) -> WorldState:
        return self.mut.state


_FREE_VERBS = {"listen", "wait", "shout", "spill", "hide", "jump", "rest", "improvise"}


class Engine:
    def __init__(self, world: World) -> None:
        self.world = world
        self._interactions_by_id = {it.id: it for it in world.interactions}

    # ------------------------------------------------------------------ setup
    def new_state(self, mug: MugIdentity, settings: AdventureSettings, seed: str) -> WorldState:
        w = self.world
        state = WorldState(
            content_version=w.meta.content_version,
            seed=seed,
            location=w.meta.start_location,
            clock_start=w.meta.start_clock,
            mug=mug,
            settings=settings,
            stats=initial_stats(mug.drink, list(mug.traits)),
            visited=[w.meta.start_location],
            discovered=[w.meta.start_location],
        )
        for item in w.items.values():
            if item.initial is None:
                continue
            holder = item.initial
            if holder in w.npcs:
                holder = f"npc:{holder}"
            state.item_locations[item.id] = holder
        bonus = 10 if "charming" in mug.traits else 0
        for npc in w.npcs.values():
            state.npcs[npc.id] = NpcState(
                location=npc.location,
                relationship=min(100, npc.relationship + bonus),
                mood=npc.mood,
            )
        for quest_id in w.quests:
            state.quests[quest_id] = QuestState()
        mut = Mutator(w, state)
        for quest_id in w.meta.initial_quests:
            mut.start_quest(quest_id)
        mut.refresh_statuses()
        return state

    def intro(self) -> dict[str, str]:
        return self.world.meta.intro

    def initial_events(self, state: WorldState) -> list[GameEvent]:
        return [
            GameEvent(
                "journal",
                {
                    "entry_kind": "quest",
                    "title": self.world.quests[q].name,
                    "body": self.world.quests[q].description,
                    "location": state.location,
                    "participants": [],
                    "decision": "",
                },
            )
            for q in self.world.meta.initial_quests
        ]

    # ------------------------------------------------------------------ scene
    def location(self, state: WorldState) -> Location:
        return self.world.locations[state.location]

    def visible_exits(self, state: WorldState) -> list[Exit]:
        loc = self.location(state)
        return [ex for ex in loc.exits if all_hold(ex.visible_if, self.world, state)]

    def exit_allowed(self, state: WorldState, loc: Location, ex: Exit) -> bool:
        if f"{loc.id}>{ex.to}" in state.unlocked_exits:
            return True
        return all_hold(ex.conditions, self.world, state)

    def visible_features(self, state: WorldState) -> list[Any]:
        return [f for f in self.location(state).features if all_hold(f.visible_if, self.world, state)]

    def present_npcs(self, state: WorldState) -> list[str]:
        return location_npcs(self.world, state, state.location)

    def remote_npcs(self, state: WorldState) -> list[str]:
        out: list[str] = []
        for view in self.location(state).views:
            out.extend(location_npcs(self.world, state, view))
        return out

    def interpret(self, state: WorldState, text: str, last_npc: str | None = None) -> Intent:
        """Free text → validated intent, using the conversation context when helpful."""
        partner = self.conversation_partner(state, last_npc)
        intent = parse(text, self.candidates(state), partner)
        if intent.verb == "improvise" and not intent.injection and partner:
            npc = self.world.npcs[partner]
            if self._match_topic(npc, state, text) is not None:
                return intent.model_copy(update={"verb": "talk", "target": partner, "confidence": 0.6})
        return intent

    def conversation_partner(self, state: WorldState, last_npc: str | None) -> str | None:
        """Who an unaddressed line of speech is meant for: the last interlocutor if still
        around, otherwise the only character in sight."""
        around = self.present_npcs(state) + self.remote_npcs(state)
        if last_npc in around:
            return last_npc
        return around[0] if len(around) == 1 else None

    def candidates(self, state: WorldState) -> list[Candidate]:
        w = self.world
        out: list[Candidate] = []
        for item_id in state.inventory():
            item = w.items[item_id]
            out.append(Candidate(item_id, "item", _kw(item.keywords, item.name), in_inventory=True))
        for item_id in state.items_at(state.location):
            item = w.items[item_id]
            out.append(Candidate(item_id, "item", _kw(item.keywords, item.name)))
        for feat in self.visible_features(state):
            out.append(Candidate(feat.id, "feature", _kw(feat.keywords, feat.name)))
        for npc_id in self.present_npcs(state):
            npc = w.npcs[npc_id]
            out.append(Candidate(npc_id, "npc", _kw(npc.keywords, npc.name)))
        for npc_id in self.remote_npcs(state):
            npc = w.npcs[npc_id]
            out.append(Candidate(npc_id, "npc", _kw(npc.keywords, npc.name), remote=True))
        for ex in self.visible_exits(state):
            dest = w.locations[ex.to]
            out.append(Candidate(f"exit:{ex.to}", "exit", _kw(ex.keywords, dest.name)))
        for ab_id in state.abilities:
            ab = w.abilities[ab_id]
            out.append(Candidate(ab_id, "ability", _kw(ab.keywords, ab.name)))
        out.append(Candidate("self", "self", list(SELF_KEYWORDS)))
        return out

    # ---------------------------------------------------------------- resolve
    def resolve(self, current: WorldState, intent: Intent) -> TurnOutcome:
        state = current.model_copy(deep=True)
        mut = Mutator(self.world, state)
        mut.player_input = intent.raw
        if state.finished:
            mut.say(M["game_over"])
            return TurnOutcome(intent, state, mut.messages, mut.events, meta=True, suggestions=[])
        state.turn += 1
        ctx = _Ctx(mut, intent, make_rng(state.seed, state.turn))
        self._dispatch(ctx)
        if not ctx.meta:
            self._tick(ctx)
        mut.refresh_statuses()
        self._auto_achievements(mut)
        outcome = TurnOutcome(
            intent=intent,
            state=state,
            messages=mut.messages,
            events=mut.events,
            check=ctx.check,
            success=ctx.success,
            minutes=0 if ctx.meta else ctx.minutes,
            meta=ctx.meta,
            dialogue_npc=ctx.dialogue_npc,
            topic=ctx.topic,
        )
        outcome.suggestions = self.suggestions(state)
        return outcome

    def _dispatch(self, ctx: _Ctx) -> None:
        intent = ctx.intent
        if intent.injection:
            ctx.mut.say(M["injection"])
            ctx.minutes = 1
            return
        if not self._validate_mentions(ctx):
            ctx.mut.say(M["not_here"])
            ctx.minutes = 1
            ctx.success = False
            return
        if intent.verb in META_VERBS:
            ctx.meta = True
            getattr(self, f"_v_{intent.verb}")(ctx)
            return
        if intent.verb == "look" and intent.target:
            intent = intent.model_copy(update={"verb": "examine"})
            ctx.intent = intent
        if self._run_interaction(ctx):
            return
        getattr(self, f"_v_{intent.verb}")(ctx)

    def _validate_mentions(self, ctx: _Ctx) -> bool:
        """An intent may only reference entities that exist in the current scene."""
        mentions = ctx.intent.mentions()
        if not mentions:
            return True
        ids = {c.id for c in self.candidates(ctx.s)}
        if ctx.intent.verb == "ability":
            ids |= set(ctx.s.abilities)
        return mentions <= ids

    # ---------------------------------------------------------- interactions
    def match_interactions(self, state: WorldState, intent: Intent) -> list[Interaction]:
        if intent.interaction:
            chosen = self._interactions_by_id.get(intent.interaction)
            if chosen and self._interaction_applies(state, chosen, intent, explicit=True):
                return [chosen]
            return []
        found: list[tuple[int, int, Interaction]] = []
        for it in self.world.interactions:
            if self._interaction_applies(state, it, intent, explicit=False):
                specificity = len({x for x in (it.target, it.item) if x})
                found.append((it.priority, specificity, it))
        found.sort(key=lambda t: (-t[0], -t[1]))
        return [t[2] for t in found]

    def _interaction_applies(
        self, state: WorldState, it: Interaction, intent: Intent, explicit: bool
    ) -> bool:
        if intent.verb not in it.verbs:
            return False
        if it.at is not None:
            at = [it.at] if isinstance(it.at, str) else it.at
            if state.location not in at:
                return False
        mentions = intent.mentions()
        if it.target and it.target not in mentions:
            return False
        if it.item and it.item not in mentions:
            # "abrir a porta" while carrying the key: the instrument is implied — but only
            # when the player didn't name a different carried item.
            carried = set(state.inventory())
            implied = intent.verb == "use" and it.item in carried and not (mentions & carried)
            if not implied:
                return False
        if not it.target and not it.item and mentions and intent.verb not in _FREE_VERBS:
            return False
        if it.keywords and not explicit:
            norm = normalize(intent.raw)
            if not any(f" {normalize(k).strip()} " in norm for k in it.keywords):
                return False
        return all_hold(it.conditions, self.world, state)

    def _run_interaction(self, ctx: _Ctx) -> bool:
        s = ctx.s
        for it in self.match_interactions(s, ctx.intent):
            if it.once and it.id in s.interactions_done:
                if it.once_text:
                    ctx.mut.say(it.once_text)
                    ctx.minutes = 1
                    return True
                continue
            self._apply_interaction(ctx, it)
            return True
        return False

    def _apply_interaction(self, ctx: _Ctx, it: Interaction) -> None:
        mut, s = ctx.mut, ctx.s
        ctx.minutes = it.minutes
        ctx.energy = it.energy
        for npc_id in self._npcs_in(it):
            mut.meet(npc_id)
            ctx.dialogue_npc = npc_id
        if it.check:
            result = self._roll(ctx, it.check, it.id)
            if not result.success:
                ctx.success = False
                mut.say(it.fail_text or M["improvise_fail"])
                scale = 0.5 if result.outcome == "partial" else 1.0
                self._apply_scaled(mut, it.fail_effects, scale)
                return
        ctx.success = True
        mut.say(it.text)
        if it.once:
            s.interactions_done.append(it.id)
        mut.apply_all(it.effects)

    def _npcs_in(self, it: Interaction) -> list[str]:
        return [x for x in (it.target, it.item) if x and x in self.world.npcs]

    def _apply_scaled(self, mut: Mutator, effects: list[Any], scale: float) -> None:
        for e in effects:
            if scale != 1.0 and e.stats:
                e = e.model_copy(update={"stats": {k: v * scale for k, v in e.stats.items()}})
            mut.apply(e)

    def _roll(self, ctx: _Ctx, check: Check, salt: str) -> CheckResult:
        s = ctx.s
        bonus = sum(v for k, v in check.bonus_ability.items() if k in s.abilities)
        bonus += sum(v for k, v in check.bonus_item.items() if s.item_locations.get(k) == INVENTORY)
        for npc_id, per in check.bonus_rel.items():
            bonus += (s.npcs[npc_id].relationship // 20) * per
        result = roll_check(make_rng(s.seed, s.turn, salt), s, check.stat, check.dc, bonus)
        ctx.check = result
        ctx.mut.emit("check", None, **result.as_dict())
        return result

    # ------------------------------------------------------------------ verbs
    def _v_look(self, ctx: _Ctx) -> None:
        s = ctx.s
        loc = self.location(s)
        parts = [loc.description]
        seen = self._scene_summary(s)
        if seen:
            parts.append(seen)
        ctx.mut.say(join(parts, "\n\n"))
        for feat in self.visible_features(s):
            ctx.mut.discover(feat.id)
        for npc_id in self.present_npcs(s):
            ctx.mut.discover(npc_id)
        ctx.minutes = 2
        ctx.energy = 0.5

    def _scene_summary(self, s: WorldState) -> dict[str, str]:
        w = self.world
        out: dict[str, str] = {}
        for lang in ("pt-BR", "en"):
            bits: list[str] = []
            npcs = [tr(w.npcs[n].name, lang) for n in self.present_npcs(s)]
            remote = [tr(w.npcs[n].name, lang) for n in self.remote_npcs(s)]
            items = [tr(w.items[i].name, lang) for i in s.items_at(s.location)]
            if npcs:
                bits.append(("Aqui está: " if lang == "pt-BR" else "Here: ") + ", ".join(npcs) + ".")
            if remote:
                bits.append(
                    ("Lá fora, através do vidro: " if lang == "pt-BR" else "Outside, through the glass: ")
                    + ", ".join(remote)
                    + "."
                )
            if items:
                bits.append(("Você nota: " if lang == "pt-BR" else "You notice: ") + ", ".join(items) + ".")
            exits = [tr(ex.label, lang) for ex in self.visible_exits(s)]
            if exits:
                bits.append(("Caminhos: " if lang == "pt-BR" else "Ways: ") + "; ".join(exits) + ".")
            out[lang] = " ".join(bits)
        return out if out.get("pt-BR") else {}

    def _v_examine(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        target = ctx.intent.target
        ctx.minutes = 2
        ctx.energy = 0.5
        if target is None:
            self._v_look(ctx)
            return
        if target == "self":
            mut.say(self._self_description(s))
        elif target in w.items:
            mut.say(w.items[target].description)
            mut.discover(target)
        elif target in w.npcs:
            mut.say(w.npcs[target].description)
            mut.discover(target)
        elif target.startswith("exit:"):
            dest = w.locations[target[5:]]
            ex = next(e for e in self.location(s).exits if e.to == dest.id)
            mut.say(join([ex.label, dest.short], ": "))
        else:
            feat = next((f for f in self.visible_features(s) if f.id == target), None)
            if feat is None:
                mut.say(M["not_here"])
                return
            mut.say(feat.description)
            mut.discover(feat.id)
        ctx.success = True

    def _self_description(self, s: WorldState) -> dict[str, str]:
        st = s.stats
        if st.integrity <= BALANCE.shattered_at:
            condition = M["self_shattered"]
        elif st.integrity <= BALANCE.cracked_at:
            condition = M["self_cracked"]
        else:
            condition = M["self_ok"]
        return fmt(
            M["self_examine"],
            material=MATERIAL_NAMES[s.mug.material],
            style=STYLE_NAMES[s.mug.style],
            drink=DRINK_NAMES[s.mug.drink],
            temperature=round(st.temperature),
            color_name=_color_name(s.mug.color),
            condition=condition,
        )

    def _v_go(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        loc = self.location(s)
        exits = self.visible_exits(s)
        target = ctx.intent.target
        if target is None or not target.startswith("exit:"):
            if len(exits) == 1 and target is None:
                target = f"exit:{exits[0].to}"
            else:
                ctx.meta = not exits
                labels = lt(
                    "; ".join(tr(e.label, "pt-BR") for e in exits),
                    "; ".join(tr(e.label, "en") for e in exits),
                )
                mut.say(fmt(M["which_exit"], exits=labels) if exits else M["no_exits"])
                ctx.minutes = 1
                return
        dest_id = target[5:]
        ex = next((e for e in exits if e.to == dest_id), None)
        if ex is None:
            mut.say(M["not_here"])
            ctx.minutes = 1
            return
        self._traverse(ctx, loc, ex)

    def _traverse(self, ctx: _Ctx, loc: Location, ex: Exit) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        if not self.exit_allowed(s, loc, ex):
            mut.say(ex.blocked_text or M["exit_blocked"])
            ctx.minutes = 1
            ctx.success = False
            return
        cost = energy_cost(s, ex.energy)
        if ex.energy >= 6 and s.stats.energy < cost:
            mut.say(M["too_tired"])
            ctx.minutes = 1
            ctx.success = False
            return
        ctx.minutes = ex.minutes
        ctx.energy = ex.energy
        if ex.check:
            result = self._roll(ctx, ex.check, f"exit:{ex.to}")
            if not result.success:
                ctx.success = False
                mut.say(ex.fail_text or M["travel_fail_default"])
                self._apply_scaled(mut, ex.fail_effects, 0.5 if result.outcome == "partial" else 1.0)
                return
        ctx.success = True
        mut.say(ex.text or fmt(M["travel"], place=w.locations[ex.to].name))
        mut.enter_location(ex.to)
        dest = w.locations[ex.to]
        if s.location == dest.id:
            mut.say(dest.description if ex.to not in _visited_before(mut) else dest.short)

    def _v_take(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        item_id = ctx.intent.target or ctx.intent.item
        ctx.minutes = 1
        if item_id is None or item_id not in w.items:
            mut.say(M["not_here"])
            return
        item = w.items[item_id]
        where = s.item_locations.get(item_id)
        if where == INVENTORY:
            mut.say(fmt(M["already_have"], item=item.name))
            ctx.meta = True
            return
        if where != s.location:
            mut.say(M["not_here"])
            return
        if not item.portable:
            mut.say(fmt(M["not_portable"], item=item.name))
            ctx.success = False
            return
        carried = sum(w.items[i].weight for i in s.inventory())
        if carried + item.weight > DIFFICULTY[s.settings.difficulty].capacity:
            mut.say(M["too_heavy"])
            ctx.success = False
            return
        mut.move_item(item_id, INVENTORY)
        mut.say(fmt(M["taken"], item=item.name))
        ctx.success = True
        ctx.energy = 1 + item.weight

    def _v_drop(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        item_id = ctx.intent.target or ctx.intent.item
        ctx.minutes = 1
        if item_id is None or s.item_locations.get(item_id) != INVENTORY:
            mut.say(
                fmt(M["not_carrying"], item=w.items[item_id].name) if item_id in w.items else M["not_here"]
            )
            return
        mut.move_item(item_id, s.location)
        mut.say(fmt(M["dropped"], item=w.items[item_id].name))
        ctx.success = True

    def _v_use(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        target = ctx.intent.target or ctx.intent.item
        ctx.minutes = 2
        if target is None:
            mut.say(M["use_nothing"])
            return
        loc = self.location(s)
        if loc.heat is not None and target in {f.id for f in loc.features if f.heat_source}:
            self._v_warm(ctx)
            return
        mut.say(fmt(M["nothing_happens"], thing=self._name(target)))
        ctx.success = False

    def _v_combine(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        a, b = ctx.intent.target, ctx.intent.item
        ctx.minutes = 4
        if not a or not b:
            mut.say(M["combine_need_two"])
            return
        for r in w.recipes:
            if set(r.inputs) == {a, b} and all_hold(r.conditions, w, s):
                if not all(s.item_locations.get(i) == INVENTORY for i in r.inputs):
                    break
                for i in r.inputs:
                    mut.move_item(i, "void")
                mut.move_item(r.output, INVENTORY)
                mut.say(r.text)
                mut.apply_all(r.effects)
                mut.add_xp(BALANCE.xp_per_discovery)
                ctx.success = True
                return
        mut.say(fmt(M["cant_combine"], a=self._name(a), b=self._name(b)))
        ctx.success = False

    def _talk_target(self, ctx: _Ctx) -> str | None:
        s, mut = ctx.s, ctx.mut
        target = ctx.intent.target
        if target and target in self.world.npcs:
            return target
        if target and target.startswith("exit:"):
            mut.say(M["not_here"])
            return None
        if target:
            mut.say(fmt(M["talk_object"], thing=self._name(target)))
            return None
        npcs = self.present_npcs(s) + self.remote_npcs(s)
        if len(npcs) == 1:
            return npcs[0]
        if not npcs:
            mut.say(M["talk_nobody"])
        else:
            names = lt(
                *(", ".join(tr(self.world.npcs[n].name, lang) for n in npcs) for lang in ("pt-BR", "en"))
            )
            mut.say(fmt(M["talk_whom"], npcs=names))
            ctx.meta = True
        return None

    def _v_talk(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        npc_id = self._talk_target(ctx)
        ctx.minutes = 3
        ctx.energy = 0.5
        if npc_id is None:
            return
        npc = w.npcs[npc_id]
        first_meeting = not s.npcs[npc_id].met
        ctx.dialogue_npc = npc_id
        ctx.success = True
        topic = self._match_topic(npc, s, ctx.intent.raw)
        greeting = next((g for g in npc.greetings if all_hold(g.conditions, w, s)), None)
        mut.meet(npc_id)
        if topic is not None:
            ctx.topic = topic.id
            if first_meeting and greeting:
                mut.say(greeting.text)
            mut.say(topic.text)
            state = s.npcs[npc_id]
            if topic.id not in state.topics_heard:
                state.topics_heard.append(topic.id)
                mut.emit("topic", None, npc=npc_id, topic=topic.id)
                mut.apply_all(topic.effects)
            return
        if greeting and (first_meeting or not self._mentions_topic_words(ctx.intent.raw, npc)):
            mut.say(greeting.text)
        else:
            mut.say(ctx.rng.choice(npc.smalltalk))

    def _mentions_topic_words(self, raw: str, npc: Npc) -> bool:
        words = [w for w in normalize(raw).split() if len(w) > 3]
        names = {k for k in normalize(" ".join(npc.keywords)).split()}
        return any(w not in names and w not in _TALK_FILLER for w in words)

    def _match_topic(self, npc: Npc, s: WorldState, raw: str) -> Any:
        norm = normalize(raw)
        # The character's own name must not count as a topic ("falar com dona doce").
        for kw in sorted(_kw(npc.keywords, npc.name), key=len, reverse=True):
            norm = norm.replace(f" {normalize(kw).strip()} ", " ")
        best, best_score = None, 0
        for topic in npc.topics:
            if topic.once and topic.id in s.npcs[npc.id].topics_heard:
                continue
            if not all_hold(topic.conditions, self.world, s):
                continue
            score = sum(
                len(k)
                for k in topic.keywords
                if f" {normalize(k).strip()} " in norm or f" {normalize(k).strip()}s " in norm
            )
            if score > best_score:
                best, best_score = topic, score
        return best

    def _v_befriend(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        npc_id = self._talk_target(ctx)
        ctx.minutes = 4
        if npc_id is None:
            return
        if npc_id in self.remote_npcs(s) and npc_id not in self.present_npcs(s):
            pass  # befriending through glass is allowed: gestures and voice.
        npc = w.npcs[npc_id]
        mut.meet(npc_id)
        ctx.dialogue_npc = npc_id
        key = f"befriend:{npc_id}"
        if s.counters.get(key, 0) >= 3:
            mut.say(ctx.rng.choice(npc.smalltalk))
            ctx.success = True
            return
        check = Check(stat="courage", dc=npc.befriend_dc, bonus_rel={npc_id: 1})
        result = self._roll(ctx, check, key)
        if result.success:
            mut.change_rel(npc_id, 5)
            s.counters[key] = s.counters.get(key, 0) + 1
            mut.say(fmt(M["befriend_ok"], npc=npc.name))
            ctx.success = True
        else:
            mut.say(fmt(M["befriend_fail"], npc=npc.name))
            ctx.success = False

    def _v_give(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        npc_id, item_id = ctx.intent.target, ctx.intent.item
        ctx.minutes = 2
        if item_id is None or s.item_locations.get(item_id) != INVENTORY:
            mut.say(M["give_need_item"])
            return
        if npc_id is None or npc_id not in w.npcs:
            npc_id = self._talk_target(ctx)
            if npc_id is None:
                return
        if npc_id not in self.present_npcs(s):
            mut.say(M["give_remote"])
            ctx.success = False
            return
        npc, item = w.npcs[npc_id], w.items[item_id]
        mut.meet(npc_id)
        ctx.dialogue_npc = npc_id
        if item_id in npc.dislikes:
            mut.change_rel(npc_id, -10)
            mut.say(fmt(M["give_reject"], npc=npc.name, item=item.name))
            ctx.success = False
            return
        mut.move_item(item_id, f"npc:{npc_id}")
        s.npcs[npc_id].gifts += 1
        liked = item_id in npc.likes
        mut.change_rel(npc_id, 15 if liked else 3)
        mut.say(fmt(M["give_accept_like" if liked else "give_accept"], npc=npc.name, item=item.name))
        ctx.success = True

    def _v_jump(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        loc = self.location(s)
        jump_exit = next((e for e in self.visible_exits(s) if e.kind == "jump"), None)
        if jump_exit:
            self._traverse(ctx, loc, jump_exit)
            return
        ctx.minutes = 1
        ctx.energy = 6
        mut.say(M["jump_ok"])
        ctx.success = True

    def _v_hide(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        ctx.minutes = 3
        ctx.energy = 2
        result = self._roll(ctx, Check(stat="creativity", dc=10, bonus_ability={"camouflage": 4}), "hide")
        if result.success:
            if "hidden" not in s.statuses:
                s.statuses.append("hidden")
            mut.say(M["hide_ok"])
            ctx.success = True
        else:
            mut.say(M["hide_fail"])
            ctx.success = False

    def _v_rest(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        ctx.minutes = BALANCE.rest_minutes
        ctx.energy = 0
        gain = BALANCE.rest_energy * DIFFICULTY[s.settings.difficulty].rest_bonus
        if "cold" in s.statuses:
            gain /= 2
        mut.change_stat("energy", gain, "rest")
        mut.say(M["rest"])
        if s.stats.temperature > self.location(s).ambient_temp + 10:
            mut.say(M["rest_cold"])
        ctx.success = True

    def _v_spill(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        ctx.minutes = 1
        ctx.energy = 1
        if s.stats.coffee <= 0:
            mut.say(M["spill_empty"])
            ctx.success = False
            return
        mut.change_stat("coffee", -BALANCE.spill_amount, "spill")
        mut.say(M["spill"])
        ctx.success = True

    def _v_shout(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        ctx.minutes = 1
        ctx.energy = 2
        mut.say(M["shout"])
        if s.counters.get("shouts", 0) < 3:
            mut.change_stat("courage", 1, "shout")
        s.counters["shouts"] = s.counters.get("shouts", 0) + 1
        if "hidden" in s.statuses:
            s.statuses.remove("hidden")
        ctx.success = True

    def _v_listen(self, ctx: _Ctx) -> None:
        mut = ctx.mut
        loc = self.location(ctx.s)
        mut.say(loc.sounds or M["listen_default"])
        ctx.minutes = 2
        ctx.energy = 0
        ctx.success = True

    def _v_wait(self, ctx: _Ctx) -> None:
        ctx.mut.say(M["wait"])
        ctx.minutes = BALANCE.wait_minutes
        ctx.energy = 0
        ctx.success = True

    def _v_warm(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        loc = self.location(s)
        ctx.minutes = 5
        ctx.energy = 0.5
        if loc.heat is None:
            mut.say(M["warm_none"])
            ctx.success = False
            return
        before = s.stats.temperature
        target = min(loc.heat, before + BALANCE.warm_step)
        if target > before:
            mut.change_stat("temperature", target - before, "warm")
        if loc.heat >= BALANCE.overheat_at and before >= 85:
            mut.change_stat("integrity", -damage_amount(s, 5), "overheat")
            mut.say(M["warm_overheat"])
        else:
            mut.say(M["warm_ok"])
        ctx.success = True

    def _v_ride(self, ctx: _Ctx) -> None:
        ctx.mut.say(M["ride_no"])
        ctx.minutes = 1
        ctx.success = False

    def _v_attack(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        target = ctx.intent.target
        ctx.minutes = 1
        ctx.energy = 5
        mut.say(M["attack"])
        mut.change_stat("integrity", -damage_amount(s, 3), "attack")
        if target in w.npcs:
            mut.change_rel(target, -15)
            s.npcs[target].mood = "wary"
            mut.say(fmt(M["attack_npc"], npc=w.npcs[target].name))
        ctx.success = False

    def _v_ability(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        ab_id = ctx.intent.target
        ctx.minutes = 2
        if ab_id not in s.abilities or ab_id not in w.abilities:
            mut.say(M["ability_unknown"])
            ctx.meta = True
            return
        ab = w.abilities[ab_id]
        if ab.kind == "passive":
            mut.say(fmt(M["ability_passive"], ability=ab.name))
            ctx.meta = True
            return
        if s.cooldowns.get(ab_id, 0) > 0:
            mut.say(fmt(M["ability_cooldown"], ability=ab.name))
            ctx.minutes = 1
            return
        if ab.min_temperature is not None and s.stats.temperature < ab.min_temperature:
            mut.say(fmt(M["ability_too_cold"], ability=ab.name))
            ctx.minutes = 1
            return
        if s.stats.energy < energy_cost(s, ab.cost_energy) or s.stats.coffee < ab.cost_coffee:
            mut.say(fmt(M["ability_cost"], ability=ab.name))
            ctx.minutes = 1
            return
        ctx.energy = ab.cost_energy
        if ab.cost_coffee:
            mut.change_stat("coffee", -ab.cost_coffee, ab_id)
        if ab.cooldown:
            s.cooldowns[ab_id] = ab.cooldown
        if ab.text:
            mut.say(ab.text)
        mut.apply_all(ab.effects)
        mut.emit("ability_used", None, ability=ab_id)
        ctx.success = True

    def _v_improvise(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        ctx.minutes = 3
        ctx.energy = 2
        result = self._roll(ctx, Check(stat="creativity", dc=11), "improvise")
        if result.success:
            mut.say(M["improvise_ok"])
            if s.counters.get("improvise_xp", 0) < 10:
                s.counters["improvise_xp"] = s.counters.get("improvise_xp", 0) + 1
                mut.add_xp(3)
                if s.counters["improvise_xp"] % 3 == 0:
                    mut.change_stat("creativity", 1, "improvise")
        elif result.outcome == "partial":
            mut.say(M["improvise_partial"])
        else:
            mut.say(M["improvise_fail"])
        ctx.success = result.success

    def _v_inventory(self, ctx: _Ctx) -> None:
        s, w = ctx.s, self.world
        items = s.inventory()
        if not items:
            ctx.mut.say(M["inventory_empty"])
            return
        names = lt(*(", ".join(tr(w.items[i].name, lang) for i in items) for lang in ("pt-BR", "en")))
        ctx.mut.say(fmt(M["inventory"], items=names))

    def _v_status(self, ctx: _Ctx) -> None:
        st = ctx.s.stats
        ctx.mut.say(
            fmt(
                M["status"],
                temperature=round(st.temperature),
                coffee=round(st.coffee),
                integrity=round(st.integrity),
                energy=round(st.energy),
            )
        )

    def _v_help(self, ctx: _Ctx) -> None:
        ctx.mut.say(M["help"])

    # ------------------------------------------------------------- the clock
    def _tick(self, ctx: _Ctx) -> None:
        s, mut = ctx.s, ctx.mut
        s.minutes += ctx.minutes
        loc = self.location(s)
        before_t = s.stats.temperature
        if s.stats.coffee > 0:
            new_t = cool(before_t, loc.ambient_temp, ctx.minutes, cooling_multiplier(s))
            mut.change_stat("temperature", new_t - before_t, "ambient")
        if ctx.energy:
            mut.change_stat("energy", -energy_cost(s, ctx.energy), "effort")
        if s.stats.integrity <= BALANCE.cracked_at and s.stats.coffee > 0:
            mut.change_stat("coffee", -BALANCE.crack_leak_per_turn, "leak")
        for ab_id in list(s.cooldowns):
            s.cooldowns[ab_id] -= 1
            if s.cooldowns[ab_id] <= 0:
                del s.cooldowns[ab_id]
        if before_t >= BALANCE.lukewarm_at > s.stats.temperature:
            mut.say(M["cooling_warn"])
        if not any(e.kind in ("moved", "quest_completed", "ending") for e in mut.events):
            self._random_event(ctx)
        if s.stats.integrity <= 0 and not s.defeated:
            s.defeated = True
            mut.emit("defeat", M["defeat"])
            mut.journal_auto("defeat", lt("Cacos", "Shards"), M["defeat"])

    def _random_event(self, ctx: _Ctx) -> None:
        s, w, mut = ctx.s, self.world, ctx.mut
        if s.turn - s.last_event_turn < BALANCE.event_cooldown_turns:
            return
        rng = make_rng(s.seed, s.turn, "event")
        if rng.random() > BALANCE.event_chance:
            return
        region = self.location(s).region
        pool = [
            ev
            for ev in w.events
            if region in ev.regions
            and not (ev.once and ev.id in s.events_seen)
            and all_hold(ev.conditions, w, s)
        ]
        if not pool:
            return
        ev = rng.choices(pool, weights=[e.weight for e in pool])[0]
        s.last_event_turn = s.turn
        if ev.id not in s.events_seen:
            s.events_seen.append(ev.id)
        mut.emit("random_event", ev.text, event=ev.id)
        mut.apply_all(ev.effects)

    def _auto_achievements(self, mut: Mutator) -> None:
        s, w = mut.state, self.world
        rules: dict[str, bool] = {
            "first_friend": any(n.relationship >= 50 for n in s.npcs.values()),
            "best_friends": any(n.relationship >= 80 for n in s.npcs.values()),
            "social_mug": sum(1 for n in s.npcs.values() if n.met) >= 6,
            "explorer": len(s.visited) >= 12,
            "cartographer": len(s.visited) >= len([x for x in w.locations.values() if not x.pseudo]),
            "close_call": 0 < s.stats.integrity <= BALANCE.shattered_at,
            "seasoned": s.stats.level >= 3,
        }
        for ach_id, ok in rules.items():
            if ok and ach_id in w.achievements and ach_id not in s.achievements:
                s.achievements.append(ach_id)
                mut.emit("achievement", fmt(M["achievement"], name=w.achievements[ach_id].name), id=ach_id)

    # ------------------------------------------------------------ suggestions
    def suggestions(self, s: WorldState, limit: int = 6) -> list[Suggestion]:
        if s.finished:
            return []
        w = self.world
        out: list[Suggestion] = []
        seen: set[tuple[str, str | None, str | None, str | None]] = set()

        def add(sug: Suggestion) -> None:
            key = (sug.verb, sug.target, sug.item, sug.interaction)
            if key not in seen and len(out) < limit:
                seen.add(key)
                out.append(sug)

        scripted = [
            it
            for it in w.interactions
            if it.suggest
            and (it.at is None or s.location in ([it.at] if isinstance(it.at, str) else it.at))
            and not (it.once and it.id in s.interactions_done)
            and all_hold(it.conditions, w, s)
            and self._mentions_visible(s, it)
        ]
        scripted.sort(key=lambda it: -it.priority)
        for it in scripted[:4]:
            assert it.suggest is not None
            add(Suggestion(it.suggest, it.verbs[0], it.target, it.item, "story", it.id))
        for npc_id in self.present_npcs(s) + self.remote_npcs(s):
            npc = w.npcs[npc_id]
            add(Suggestion(fmt(_TALK_LABEL, npc=npc.name), "talk", npc_id, None, "talk"))
            if s.npcs[npc_id].met:
                for topic in npc.topics:
                    if (
                        topic.label
                        and topic.id not in s.npcs[npc_id].topics_heard
                        and all_hold(topic.conditions, w, s)
                    ):
                        add(Suggestion(topic.label, "talk", npc_id, None, "talk"))
                        break
        if ("cold" in s.statuses or "lukewarm" in s.statuses) and self.location(s).heat is not None:
            add(Suggestion(_WARM_LABEL, "warm", None, None, "care"))
        if "tired" in s.statuses:
            add(Suggestion(_REST_LABEL, "rest", None, None, "care"))
        for item_id in s.items_at(s.location):
            if w.items[item_id].portable:
                add(Suggestion(fmt(_TAKE_LABEL, item=w.items[item_id].name), "take", item_id, None, "item"))
                break
        exits = sorted(self.visible_exits(s), key=lambda e: e.to in s.visited)
        for ex in exits[:2]:
            add(Suggestion(ex.label, "go", f"exit:{ex.to}", None, "move"))
        for feat in self.visible_features(s):
            if feat.id not in s.discovered:
                add(Suggestion(fmt(_EXAMINE_LABEL, thing=feat.name), "examine", feat.id, None, "examine"))
                break
        if len(out) < limit:
            add(Suggestion(_LOOK_LABEL, "look", None, None, "examine"))
        return out

    def _mentions_visible(self, s: WorldState, it: Interaction) -> bool:
        ids = {c.id for c in self.candidates(s)}
        return all(x in ids for x in (it.target, it.item) if x)

    def _name(self, entity: str) -> dict[str, str]:
        w = self.world
        if entity in w.items:
            return w.items[entity].name
        if entity in w.npcs:
            return w.npcs[entity].name
        if entity.startswith("exit:"):
            return w.locations[entity[5:]].name
        if entity == "self":
            return lt("você mesma", "yourself")
        owner = w.feature_owner(entity)
        if owner:
            return next(f.name for f in owner.features if f.id == entity)
        return lt(entity, entity)


def _visited_before(mut: Mutator) -> set[str]:
    """Locations visited before this turn's move (so first visits get the long text)."""
    firsts = {e.data["to"] for e in mut.events if e.kind == "moved" and e.data.get("first")}
    return set(mut.state.visited) - firsts


def _kw(keywords: list[str], name: dict[str, str]) -> list[str]:
    return [*keywords, *name.values()]


_TALK_FILLER = {
    "falar",
    "conversar",
    "com",
    "sobre",
    "para",
    "talk",
    "speak",
    "with",
    "about",
    "quero",
    "want",
    "vou",
    "tentar",
    "try",
    "dizer",
    "say",
    "perguntar",
    "ask",
    "the",
    "ele",
    "ela",
}

_TALK_LABEL = lt("Conversar com {npc}", "Talk to {npc}")
_TAKE_LABEL = lt("Pegar {item}", "Take {item}")
_EXAMINE_LABEL = lt("Examinar {thing}", "Examine {thing}")
_LOOK_LABEL = lt("Olhar ao redor", "Look around")
_WARM_LABEL = lt("Aquecer-se", "Warm up")
_REST_LABEL = lt("Descansar um pouco", "Rest a while")

_COLOR_NAMES: list[tuple[str, dict[str, str]]] = [
    ("#f4efe6", lt("branca", "white")),
    ("#2f2a28", lt("preta", "black")),
    ("#b4472f", lt("terracota", "terracotta")),
    ("#2f5d8a", lt("azul", "blue")),
    ("#3f7a5a", lt("verde", "green")),
    ("#d9a441", lt("amarela", "yellow")),
    ("#8a4f7d", lt("ameixa", "plum")),
    ("#c97b84", lt("rosa", "pink")),
]


def _color_name(hex_color: str) -> dict[str, str]:
    def dist(a: str, b: str) -> int:
        return sum((int(a[i : i + 2], 16) - int(b[i : i + 2], 16)) ** 2 for i in (1, 3, 5))

    return min(_COLOR_NAMES, key=lambda pair: dist(pair[0], hex_color.lower()))[1]
