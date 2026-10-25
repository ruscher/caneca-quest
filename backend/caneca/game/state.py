"""The persistent, authoritative state of one adventure.

The state is a single validated document. Item ownership lives in exactly one map
(``item_locations``), which makes item duplication impossible by construction.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from caneca.game.content_schema import QuestStatus
from caneca.game.i18n import Lang

STATE_SCHEMA_VERSION = 1

Tone = Literal["balanced", "fantasy", "mystery", "humor", "drama", "relaxing", "survival"]
Difficulty = Literal["story", "adventure", "survival"]
NarrativeLength = Literal["short", "normal", "detailed", "cinematic"]
Material = Literal["porcelain", "stoneware", "enamel", "glass"]
Drink = Literal["black_coffee", "latte", "cappuccino", "hot_chocolate", "tea"]
Style = Literal["classic", "striped", "dotted", "floral", "minimal", "rustic"]
Personality = Literal["optimistic", "sarcastic", "shy", "philosophical", "fearless"]
Trait = Literal["brave", "creative", "sturdy", "thermal", "curious", "charming"]

INVENTORY = "inventory"
VOID = "void"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MugIdentity(_Model):
    name: str = Field(min_length=1, max_length=40)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    style: Style = "classic"
    material: Material = "porcelain"
    drink: Drink = "black_coffee"
    personality: Personality = "optimistic"
    traits: list[Trait] = Field(default_factory=list, max_length=2)


class AdventureSettings(_Model):
    tone: Tone = "balanced"
    difficulty: Difficulty = "adventure"
    narrative_length: NarrativeLength = "normal"
    language: Lang = "pt-BR"


class Stats(_Model):
    temperature: float = 80.0
    coffee: float = 75.0
    integrity: float = 95.0
    energy: float = 100.0
    courage: float = 50.0
    creativity: float = 50.0
    xp: int = 0
    level: int = 1


class NpcState(_Model):
    location: str
    relationship: int = 0
    mood: str = "neutral"
    met: bool = False
    memories: list[str] = Field(default_factory=list)
    topics_heard: list[str] = Field(default_factory=list)
    gifts: int = 0


class QuestState(_Model):
    status: QuestStatus = "inactive"
    done: list[str] = Field(default_factory=list)
    outcome: str | None = None
    started_turn: int | None = None
    finished_turn: int | None = None


class Fact(_Model):
    id: str
    text: dict[str, str]
    turn: int
    importance: int = 2
    location: str
    tags: list[str] = Field(default_factory=list)


class WorldState(_Model):
    schema_version: int = STATE_SCHEMA_VERSION
    content_version: str
    seed: str
    turn: int = 0
    minutes: int = 0
    clock_start: int = 0
    location: str
    chapter: int = 1
    mug: MugIdentity
    settings: AdventureSettings
    stats: Stats = Field(default_factory=Stats)
    statuses: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    cooldowns: dict[str, int] = Field(default_factory=dict)
    visited: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    counters: dict[str, int] = Field(default_factory=dict)
    item_locations: dict[str, str] = Field(default_factory=dict)
    npcs: dict[str, NpcState] = Field(default_factory=dict)
    unlocked_exits: list[str] = Field(default_factory=list)
    quests: dict[str, QuestState] = Field(default_factory=dict)
    interactions_done: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    discovered: list[str] = Field(default_factory=list)
    reputation: dict[str, int] = Field(default_factory=dict)
    facts: dict[str, Fact] = Field(default_factory=dict)
    last_event_turn: int = 0
    events_seen: list[str] = Field(default_factory=list)
    ending: str | None = None
    defeated: bool = False

    # Small helpers keep membership tests readable at call sites.
    def has_flag(self, flag: str) -> bool:
        return flag in self.flags

    def inventory(self) -> list[str]:
        return [i for i, where in self.item_locations.items() if where == INVENTORY]

    def items_at(self, location: str) -> list[str]:
        return [i for i, where in self.item_locations.items() if where == location]

    def quest(self, quest_id: str) -> QuestState:
        return self.quests.setdefault(quest_id, QuestState())

    @property
    def finished(self) -> bool:
        return self.ending is not None or self.defeated
