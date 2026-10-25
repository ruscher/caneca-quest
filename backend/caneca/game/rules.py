"""Explicit, testable rules for the mug's attributes.

All tuning numbers live in ``BALANCE`` and the profile tables so they can be adjusted
without touching the logic.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Literal

from caneca.game.state import Difficulty, Drink, Material, Stats, WorldState


@dataclass(frozen=True)
class Balance:
    cooling_rate: float = 0.01  # Newton cooling constant, per in-game minute
    warm_step: float = 25.0
    overheat_at: float = 92.0
    hot_at: float = 60.0
    lukewarm_at: float = 40.0
    cold_at: float = 25.0
    tired_at: float = 15.0
    cracked_at: float = 50.0
    shattered_at: float = 20.0
    crack_leak_per_turn: float = 1.0
    float_coffee_max: float = 40.0
    spill_amount: float = 10.0
    rest_energy: float = 30.0
    rest_minutes: int = 20
    wait_minutes: int = 10
    xp_per_new_location: int = 10
    xp_per_discovery: int = 5
    event_chance: float = 0.12
    event_cooldown_turns: int = 5


BALANCE = Balance()


@dataclass(frozen=True)
class DifficultyProfile:
    cooling: float
    energy_cost: float
    check_bonus: int
    damage: float
    min_integrity: float
    capacity: int
    rest_bonus: float


DIFFICULTY: dict[Difficulty, DifficultyProfile] = {
    "story": DifficultyProfile(0.6, 0.7, 2, 0.6, 5.0, 6, 1.4),
    "adventure": DifficultyProfile(1.0, 1.0, 0, 1.0, 0.0, 5, 1.0),
    "survival": DifficultyProfile(1.4, 1.25, -1, 1.3, 0.0, 4, 0.8),
}


@dataclass(frozen=True)
class MaterialProfile:
    damage: float
    cooling: float
    energy_cost: float


MATERIALS: dict[Material, MaterialProfile] = {
    "porcelain": MaterialProfile(1.0, 1.0, 1.0),
    "stoneware": MaterialProfile(0.75, 0.9, 1.15),
    "enamel": MaterialProfile(0.6, 1.25, 0.95),
    "glass": MaterialProfile(1.3, 1.05, 0.9),
}

DRINK_BONUS: dict[Drink, dict[str, float]] = {
    "black_coffee": {"energy": 0},
    "latte": {"integrity": 3},
    "cappuccino": {"creativity": 5},
    "hot_chocolate": {"courage": 5},
    "tea": {"temperature": -5, "creativity": 3},
}

TRAIT_BONUS: dict[str, dict[str, float]] = {
    "brave": {"courage": 15},
    "creative": {"creativity": 15},
    "sturdy": {"integrity": 5},
    "thermal": {},
    "curious": {},
    "charming": {},
}

STAT_LIMITS: dict[str, tuple[float, float]] = {
    "temperature": (-10.0, 100.0),
    "coffee": (0.0, 100.0),
    "integrity": (0.0, 100.0),
    "energy": (0.0, 100.0),
    "courage": (0.0, 100.0),
    "creativity": (0.0, 100.0),
}


def initial_stats(drink: Drink, traits: list[str]) -> Stats:
    stats = Stats()
    for bonus in [DRINK_BONUS[drink], *(TRAIT_BONUS[t] for t in traits)]:
        for name, value in bonus.items():
            setattr(stats, name, clamp_stat(name, getattr(stats, name) + value))
    return stats


def clamp_stat(name: str, value: float) -> float:
    lo, hi = STAT_LIMITS[name]
    return round(min(hi, max(lo, value)), 2)


def xp_for_level(level: int) -> int:
    """Total XP needed to reach ``level`` (lvl2=100, lvl3=300, lvl4=600...)."""
    return 50 * level * (level - 1)


def level_for_xp(xp: int) -> int:
    level = 1
    while xp >= xp_for_level(level + 1):
        level += 1
    return level


def cooling_multiplier(state: WorldState) -> float:
    mult = DIFFICULTY[state.settings.difficulty].cooling
    mult *= MATERIALS[state.mug.material].cooling
    if "thermal" in state.mug.traits:
        mult *= 0.85
    if "thermal_resistance" in state.abilities:
        mult *= 0.6
    return mult


def cool(temperature: float, ambient: float, minutes: int, multiplier: float) -> float:
    """Newton's law of cooling (also warms toward a hotter ambient)."""
    k = BALANCE.cooling_rate * multiplier
    return ambient + (temperature - ambient) * math.exp(-k * max(0, minutes))


def energy_cost(state: WorldState, base: float) -> float:
    mult = DIFFICULTY[state.settings.difficulty].energy_cost
    mult *= MATERIALS[state.mug.material].energy_cost
    if state.stats.temperature < BALANCE.lukewarm_at:
        mult *= 1.2
    return round(base * mult, 2)


def damage_amount(state: WorldState, base: float) -> float:
    mult = DIFFICULTY[state.settings.difficulty].damage
    mult *= MATERIALS[state.mug.material].damage
    if "sturdy" in state.mug.traits:
        mult *= 0.8
    return round(base * mult, 2)


def derive_statuses(stats: Stats) -> list[str]:
    """Statuses that follow directly from the numbers. Narrative statuses are kept apart."""
    out: list[str] = []
    t = stats.temperature
    if t >= BALANCE.overheat_at:
        out.append("overheated")
    elif t >= BALANCE.hot_at:
        out.append("hot")
    elif t < BALANCE.cold_at:
        out.append("cold")
    elif t < BALANCE.lukewarm_at:
        out.append("lukewarm")
    if stats.coffee <= 0:
        out.append("empty")
    elif stats.coffee <= BALANCE.float_coffee_max:
        out.append("buoyant")
    if stats.energy < BALANCE.tired_at:
        out.append("tired")
    if stats.integrity <= BALANCE.shattered_at:
        out.append("shattered")
    elif stats.integrity <= BALANCE.cracked_at:
        out.append("cracked")
    return out


DERIVED_STATUSES = {
    "overheated",
    "hot",
    "cold",
    "lukewarm",
    "empty",
    "buoyant",
    "tired",
    "shattered",
    "cracked",
}


CheckOutcome = Literal["critical", "success", "partial", "failure"]


@dataclass(frozen=True)
class CheckResult:
    stat: str
    dc: int
    roll: int
    modifier: int
    total: int
    outcome: CheckOutcome

    @property
    def success(self) -> bool:
        return self.outcome in ("critical", "success")

    def as_dict(self) -> dict[str, object]:
        return {
            "stat": self.stat,
            "dc": self.dc,
            "roll": self.roll,
            "modifier": self.modifier,
            "total": self.total,
            "outcome": self.outcome,
        }


def stat_modifier(state: WorldState, stat: str) -> int:
    value = getattr(state.stats, stat)
    mod = math.floor((value - 50) / 10) if stat in ("courage", "creativity") else 0
    if stat in ("energy", "integrity", "temperature"):
        mod = math.floor((value - 50) / 15)
    statuses = set(state.statuses)
    if "hot" in statuses:
        mod += 1
    if "lukewarm" in statuses:
        mod -= 1
    if "cold" in statuses:
        mod -= 3
    if "tired" in statuses:
        mod -= 2
    if "empty" in statuses and stat == "creativity":
        mod -= 2
    if "shattered" in statuses:
        mod -= 2
    if "advanced_balance" in state.abilities:
        mod += 1
    return mod + DIFFICULTY[state.settings.difficulty].check_bonus


def roll_check(rng: random.Random, state: WorldState, stat: str, dc: int, bonus: int = 0) -> CheckResult:
    roll = rng.randint(1, 20)
    modifier = stat_modifier(state, stat) + bonus
    total = roll + modifier
    if roll == 20 or total >= dc + 5:
        outcome: CheckOutcome = "critical" if roll != 1 else "partial"
    elif roll == 1:
        outcome = "failure"
    elif total >= dc:
        outcome = "success"
    elif total >= dc - 3:
        outcome = "partial"
    else:
        outcome = "failure"
    return CheckResult(stat, dc, roll, modifier, total, outcome)


def make_rng(seed: str, turn: int, salt: str = "") -> random.Random:
    """Reproducible randomness: same seed + turn + salt always yields the same rolls."""
    return random.Random(f"{seed}:{turn}:{salt}")  # noqa: S311 - game dice, not crypto
