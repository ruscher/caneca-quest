"""Typed schema of the authored world content (YAML files in ``content/``).

Content is data, not code: new places, characters and quests are added by writing
YAML that validates against these models. The engine never needs to change for that.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caneca.game.i18n import LText

Verb = Literal[
    "look",
    "examine",
    "go",
    "take",
    "drop",
    "use",
    "combine",
    "talk",
    "give",
    "jump",
    "hide",
    "rest",
    "spill",
    "shout",
    "listen",
    "wait",
    "warm",
    "befriend",
    "ride",
    "attack",
    "ability",
    "inventory",
    "status",
    "help",
    "improvise",
]
VERBS: tuple[str, ...] = Verb.__args__  # type: ignore[attr-defined]

StatName = Literal[
    "temperature",
    "coffee",
    "integrity",
    "energy",
    "courage",
    "creativity",
]
QuestKind = Literal["main", "side", "secret", "emergent", "npc", "exploration"]
QuestStatus = Literal["inactive", "active", "completed", "failed"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Condition(_Strict):
    """All specified keys must hold (logical AND). ``any``/``all``/``not`` nest."""

    flag: str | None = None
    not_flag: str | None = None
    has_item: str | None = None
    lacks_item: str | None = None
    item_at: tuple[str, str] | None = None
    at: str | list[str] | None = None
    visited: str | None = None
    stat: StatName | None = None
    gte: float | None = None
    lte: float | None = None
    rel: str | None = None
    npc_at: tuple[str, str] | None = None
    met: str | None = None
    npc_remembers: tuple[str, str] | None = None
    quest: str | None = None
    status: QuestStatus | None = None
    objective: str | None = None
    ability: str | None = None
    level_gte: int | None = None
    counter: str | None = None
    has_status: str | None = None
    lacks_status: str | None = None
    difficulty: str | None = None
    chapter_gte: int | None = None
    any: list[Condition] | None = None
    all: list[Condition] | None = None
    not_: Condition | None = Field(default=None, alias="not")

    @model_validator(mode="after")
    def _non_empty(self) -> Condition:
        if not self.model_fields_set:
            raise ValueError("condição vazia")
        uses_threshold = self.gte is not None or self.lte is not None
        if uses_threshold and not (self.stat or self.rel or self.counter):
            raise ValueError("gte/lte exigem stat, rel ou counter")
        if self.status and not self.quest:
            raise ValueError("status exige quest")
        return self


class JournalSpec(_Strict):
    title: LText
    text: LText


class FactSpec(_Strict):
    id: str
    text: LText
    importance: int = Field(default=2, ge=1, le=5)
    tags: list[str] = []
    witnesses: Literal["present", "none"] = "present"


class QuestCompleteSpec(_Strict):
    id: str
    outcome: str | None = None


class Effect(_Strict):
    """A state mutation. Several keys may be set; they apply in a fixed order.

    ``when`` makes the whole effect conditional, which lets content express alternative
    resolutions without engine code.
    """

    when: list[Condition] = []
    set_flag: str | list[str] | None = None
    clear_flag: str | list[str] | None = None
    give_item: str | None = None
    take_item: str | None = None
    place_item: tuple[str, str] | None = None
    stats: dict[StatName, float] | None = None
    set_stats: dict[StatName, float] | None = None
    rel: dict[str, int] | None = None
    npc_mood: dict[str, str] | None = None
    npc_remembers: dict[str, str] | None = None
    move_player: str | None = None
    move_npc: dict[str, str] | None = None
    unlock_exit: str | list[str] | None = None
    quest_start: str | None = None
    objective: str | None = None
    quest_complete: QuestCompleteSpec | None = None
    quest_fail: str | None = None
    xp: int | None = None
    learn: str | None = None
    journal: JournalSpec | None = None
    fact: FactSpec | None = None
    achievement: str | None = None
    discover: str | None = None
    reputation: dict[str, int] | None = None
    counter: dict[str, int] | None = None
    status_add: str | None = None
    status_remove: str | None = None
    minutes: int | None = None
    chapter: int | None = None
    ending: str | None = None


class Check(_Strict):
    stat: Literal["courage", "creativity", "energy", "integrity", "temperature"]
    dc: int = Field(ge=2, le=30)
    bonus_ability: dict[str, int] = {}
    bonus_item: dict[str, int] = {}
    bonus_rel: dict[str, int] = {}


class Feature(_Strict):
    id: str
    name: LText
    keywords: list[str]
    description: LText
    visible_if: list[Condition] = []
    heat_source: bool = False


class Exit(_Strict):
    to: str
    label: LText
    keywords: list[str] = []
    visible_if: list[Condition] = []
    conditions: list[Condition] = []
    blocked_text: LText | None = None
    check: Check | None = None
    text: LText | None = None
    fail_text: LText | None = None
    fail_effects: list[Effect] = []
    energy: float = 3
    minutes: int = 3
    kind: Literal["walk", "climb", "jump", "swim", "secret"] = "walk"


class Location(_Strict):
    id: str
    region: str
    name: LText
    description: LText
    short: LText
    ambient_temp: float
    heat: float | None = None
    dark: bool = False
    pseudo: bool = False
    views: list[str] = []
    exits: list[Exit] = []
    features: list[Feature] = []
    sounds: LText | None = None
    on_enter: list[Effect] = []
    map_pos: tuple[float, float] = (0.5, 0.5)
    tags: list[str] = []


class Item(_Strict):
    id: str
    name: LText
    keywords: list[str]
    description: LText
    portable: bool = True
    weight: int = Field(default=1, ge=0, le=10)
    initial: str | None = None
    tags: list[str] = []
    icon: str = "item"


class Topic(_Strict):
    id: str
    keywords: list[str]
    conditions: list[Condition] = []
    text: LText
    effects: list[Effect] = []
    once: bool = False
    label: LText | None = None


class Greeting(_Strict):
    conditions: list[Condition] = []
    text: LText


class Secret(_Strict):
    id: str
    text: LText
    reveal_if: list[Condition]


class Npc(_Strict):
    id: str
    name: LText
    kind: LText
    keywords: list[str]
    description: LText
    personality: LText
    voice: LText
    background: LText
    goals: LText
    secrets: list[Secret] = []
    knowledge: list[LText] = []
    location: str
    relationship: int = Field(default=0, ge=-100, le=100)
    mood: str = "neutral"
    likes: list[str] = []
    dislikes: list[str] = []
    greetings: list[Greeting]
    topics: list[Topic] = []
    smalltalk: list[LText]
    befriend_dc: int = 12
    icon: str = "npc"


class Interaction(_Strict):
    id: str
    verbs: list[Verb]
    keywords: list[str] = []
    target: str | None = None
    item: str | None = None
    at: str | list[str] | None = None
    conditions: list[Condition] = []
    check: Check | None = None
    text: LText
    effects: list[Effect] = []
    fail_text: LText | None = None
    fail_effects: list[Effect] = []
    once: bool = False
    once_text: LText | None = None
    priority: int = 0
    suggest: LText | None = None
    energy: float = 2
    minutes: int = 3


class Recipe(_Strict):
    id: str
    inputs: tuple[str, str]
    output: str
    conditions: list[Condition] = []
    text: LText
    effects: list[Effect] = []


class Objective(_Strict):
    id: str
    text: LText
    optional: bool = False


class Quest(_Strict):
    id: str
    kind: QuestKind
    name: LText
    description: LText
    objectives: list[Objective]
    auto_complete: bool = True
    xp: int = 0
    rewards: list[Effect] = []
    outcomes: dict[str, LText] = {}
    giver: str | None = None


class Ability(_Strict):
    id: str
    name: LText
    description: LText
    kind: Literal["active", "passive"]
    keywords: list[str] = []
    requires_level: int = 1
    auto_at_level: int | None = None
    cost_energy: float = 0
    cost_coffee: float = 0
    min_temperature: float | None = None
    cooldown: int = 0
    effects: list[Effect] = []
    text: LText | None = None


class RandomEvent(_Strict):
    id: str
    regions: list[str]
    conditions: list[Condition] = []
    weight: int = 1
    once: bool = False
    text: LText
    effects: list[Effect] = []


class Achievement(_Strict):
    id: str
    name: LText
    description: LText
    secret: bool = False


class Ending(_Strict):
    id: str
    name: LText
    text: LText
    kind: Literal["victory", "bittersweet", "defeat"] = "victory"


class Region(_Strict):
    id: str
    name: LText
    description: LText
    chapter: int
    palette: str = "cafe"


class Chapter(_Strict):
    number: int
    title: LText
    region: str


class WorldMeta(_Strict):
    content_version: str
    start_location: str
    start_clock: int = Field(ge=0, lt=24 * 60)
    intro: LText
    initial_quests: list[str]


class ContentFile(_Strict):
    meta: WorldMeta | None = None
    regions: list[Region] = []
    chapters: list[Chapter] = []
    locations: list[Location] = []
    items: list[Item] = []
    npcs: list[Npc] = []
    interactions: list[Interaction] = []
    recipes: list[Recipe] = []
    quests: list[Quest] = []
    abilities: list[Ability] = []
    events: list[RandomEvent] = []
    achievements: list[Achievement] = []
    endings: list[Ending] = []
