"""Attribute rules: temperature, coffee, integrity, energy, checks and progression."""

from __future__ import annotations

import dataclasses
import math

import pytest
from helpers import do, fresh, put

from caneca.game.engine import Engine
from caneca.game.mechanics import Mutator
from caneca.game.rules import (
    BALANCE,
    cool,
    cooling_multiplier,
    damage_amount,
    derive_statuses,
    energy_cost,
    initial_stats,
    level_for_xp,
    make_rng,
    roll_check,
    stat_modifier,
    xp_for_level,
)
from caneca.game.state import MugIdentity, Stats


# ---------------------------------------------------------------- temperature
def test_newton_cooling_formula():
    assert cool(80, 17, 0, 1.0) == 80
    expected = 17 + 63 * math.exp(-BALANCE.cooling_rate * 10)
    assert cool(80, 17, 10, 1.0) == pytest.approx(expected)
    # Never crosses the ambient temperature, and warms toward a hotter ambient.
    assert cool(80, 17, 100_000, 1.0) == pytest.approx(17)
    assert 10 < cool(10, 30, 50, 1.0) < 30


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"difficulty": "adventure"}, 1.0),
        ({"difficulty": "story"}, 0.6),
        ({"difficulty": "survival"}, 1.4),
    ],
)
def test_cooling_multiplier_by_difficulty(engine, kwargs, expected):
    assert cooling_multiplier(fresh(engine, **kwargs)) == pytest.approx(expected)


def test_cooling_multiplier_material_trait_and_ability(engine: Engine):
    state = fresh(engine)
    state.mug = MugIdentity(name="E", color="#ffffff", material="enamel")
    assert cooling_multiplier(state) == pytest.approx(1.25)
    state.mug = MugIdentity(name="T", color="#ffffff", traits=["thermal"])
    assert cooling_multiplier(state) == pytest.approx(0.85)
    state.abilities.append("thermal_resistance")
    assert cooling_multiplier(state) == pytest.approx(0.85 * 0.6)


def test_turn_cools_coffee_toward_location_ambient(engine: Engine):
    state = fresh(engine, location="porao")  # 11 °C cellar
    out = do(engine, state, "wait")
    loc_amb = engine.world.locations["porao"].ambient_temp
    expected = cool(80, loc_amb, BALANCE.wait_minutes, 1.0)
    assert out.state.stats.temperature == pytest.approx(expected, abs=0.01)


def test_empty_mug_does_not_change_temperature(engine: Engine):
    state = fresh(engine, location="porao")
    state.stats.coffee = 0
    out = do(engine, state, "wait")
    assert out.state.stats.temperature == 80


def test_warm_at_stove_and_overheat_interaction(engine: Engine):
    state = fresh(engine, location="cozinha")
    state.stats.temperature = 40
    out = do(engine, state, "use", "fogao")
    assert out.state.stats.temperature > 60
    hot = out.state
    hot.stats.temperature = 70
    integrity = hot.stats.integrity
    out = do(engine, hot, "use", "fogao")
    assert out.state.stats.integrity == pytest.approx(integrity - 5)


def test_default_warm_caps_at_heat_and_overheats_above_threshold(engine: Engine, world):
    loc = world.locations["cozinha"].model_copy(update={"heat": 95.0})
    hot_world = dataclasses.replace(world, locations={**world.locations, "cozinha": loc})
    eng = Engine(hot_world)
    state = fresh(eng, location="cozinha")
    state.stats.temperature = 50
    out = do(eng, state, "warm")
    assert out.state.stats.temperature <= 95
    state = out.state
    state.stats.temperature = 90
    before = state.stats.integrity
    out = do(eng, state, "warm")
    assert out.state.stats.integrity < before
    assert any(e.kind == "stat" and e.data.get("reason") == "overheat" for e in out.events)


def test_warm_without_heat_source(engine: Engine):
    out = do(engine, fresh(engine, location="salao"), "warm")
    assert out.success is False


# ---------------------------------------------------------------- coffee
def test_spill_and_buoyancy_and_empty(engine: Engine):
    state = fresh(engine, location="salao")
    for _ in range(4):
        state = do(engine, state, "spill").state
    assert state.stats.coffee == pytest.approx(35)
    assert "buoyant" in state.statuses
    state.stats.coffee = 0
    out = do(engine, state, "spill")
    assert out.success is False
    assert "empty" in out.state.statuses


def test_crack_leak_only_when_cracked(engine: Engine):
    state = fresh(engine, location="salao")
    state.stats.integrity = 60
    assert do(engine, state, "wait").state.stats.coffee == 75
    state.stats.integrity = 50
    assert do(engine, state, "wait").state.stats.coffee == 74


# ---------------------------------------------------------------- integrity
def test_damage_scaling(engine: Engine):
    adv = fresh(engine)
    assert damage_amount(adv, 10) == 10
    assert damage_amount(fresh(engine, difficulty="story"), 10) == 6
    assert damage_amount(fresh(engine, difficulty="survival"), 10) == 13
    adv.mug = MugIdentity(name="S", color="#ffffff", material="stoneware", traits=["sturdy"])
    assert damage_amount(adv, 10) == pytest.approx(10 * 0.75 * 0.8)


def test_story_mode_integrity_floor(engine: Engine):
    state = fresh(engine, difficulty="story")
    mut = Mutator(engine.world, state)
    mut.change_stat("integrity", -500)
    assert state.stats.integrity == 5


def test_adventure_defeat_at_zero(engine: Engine):
    state = fresh(engine, location="salao")
    state.stats.integrity = 1
    out = do(engine, state, "attack")
    assert out.state.stats.integrity == 0
    assert out.state.defeated
    assert "defeat" in [e.kind for e in out.events]


def test_derived_statuses():
    assert derive_statuses(Stats(temperature=95))[0] == "overheated"
    assert "cold" in derive_statuses(Stats(temperature=20))
    assert "lukewarm" in derive_statuses(Stats(temperature=30))
    assert "tired" in derive_statuses(Stats(energy=10))
    assert "cracked" in derive_statuses(Stats(integrity=50))
    assert "shattered" in derive_statuses(Stats(integrity=20))


# ---------------------------------------------------------------- energy
def test_energy_cost_multipliers(engine: Engine):
    assert energy_cost(fresh(engine), 10) == 10
    assert energy_cost(fresh(engine, difficulty="story"), 10) == 7
    assert energy_cost(fresh(engine, difficulty="survival"), 10) == 12.5
    lukewarm = fresh(engine)
    lukewarm.stats.temperature = 30
    assert energy_cost(lukewarm, 10) == 12
    heavy = fresh(engine)
    heavy.mug = MugIdentity(name="G", color="#ffffff", material="stoneware")
    assert energy_cost(heavy, 10) == 11.5


def test_rest_recovery(engine: Engine):
    state = fresh(engine, location="salao")
    state.stats.energy = 40
    assert do(engine, state, "rest").state.stats.energy == 70
    story = fresh(engine, location="salao", difficulty="story")
    story.stats.energy = 40
    assert do(engine, story, "rest").state.stats.energy == pytest.approx(82)
    cold = fresh(engine, location="salao")
    cold.stats.energy = 40
    cold.stats.temperature = 20
    cold.statuses = ["cold"]
    assert do(engine, cold, "rest").state.stats.energy == 55


# ---------------------------------------------------------------- checks
class FixedRng:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, _a: int, _b: int) -> int:
        return self.value


def test_stat_modifiers_and_status_penalties(engine: Engine):
    state = fresh(engine)
    state.statuses = []
    state.stats.courage = 50
    assert stat_modifier(state, "courage") == 0
    state.stats.courage = 75
    assert stat_modifier(state, "courage") == 2
    state.statuses = ["tired", "cold"]
    assert stat_modifier(state, "courage") == 2 - 2 - 3
    state.statuses = ["hot"]
    assert stat_modifier(state, "courage") == 3


@pytest.mark.parametrize(
    ("roll", "outcome"),
    [(20, "critical"), (15, "critical"), (12, "success"), (8, "partial"), (2, "failure"), (1, "failure")],
)
def test_check_outcomes(engine: Engine, roll, outcome):
    state = fresh(engine)
    state.statuses = []
    result = roll_check(FixedRng(roll), state, "courage", 10)  # type: ignore[arg-type]
    assert result.outcome == outcome
    assert result.success == (outcome in ("critical", "success"))


def test_checks_are_reproducible(engine: Engine):
    a = [make_rng("seed", 7, "x").randint(1, 20) for _ in range(5)]
    b = [make_rng("seed", 7, "x").randint(1, 20) for _ in range(5)]
    assert a == b
    state = fresh(engine, location="mesa_principal", seed="repro")
    first = do(engine, state, "jump")
    second = do(engine, state, "jump")
    assert first.check is not None and second.check is not None
    assert first.check.as_dict() == second.check.as_dict()
    assert first.state.model_dump() == second.state.model_dump()


# ---------------------------------------------------------------- progression
def test_level_thresholds():
    assert [xp_for_level(n) for n in (1, 2, 3, 4)] == [0, 100, 300, 600]
    assert level_for_xp(99) == 1
    assert level_for_xp(100) == 2
    assert level_for_xp(299) == 2
    assert level_for_xp(600) == 4


def test_level_up_rewards_and_auto_abilities(engine: Engine):
    state = fresh(engine)
    state.stats.energy = 10
    courage = state.stats.courage
    mut = Mutator(engine.world, state)
    mut.add_xp(100)
    assert state.stats.level == 2
    assert state.stats.energy == 100
    assert state.stats.courage == courage + 5
    assert "advanced_balance" in state.abilities
    mut.add_xp(200)
    assert state.stats.level == 3
    assert "steam_control" in state.abilities
    assert [e.data["level"] for e in mut.events if e.kind == "level_up"] == [2, 3]


def test_curious_trait_bonus_xp(engine: Engine):
    state = fresh(engine)
    state.mug = MugIdentity(name="C", color="#ffffff", traits=["curious"])
    Mutator(engine.world, state).add_xp(10)
    assert state.stats.xp == 11


def test_initial_stats_from_drink_and_traits():
    stats = initial_stats("hot_chocolate", ["brave", "sturdy"])
    assert stats.courage == 70
    assert stats.integrity == 100
    assert initial_stats("tea", []).temperature == 75


def test_movement_into_hot_room_does_not_skip_cooling(engine: Engine):
    state = put(fresh(engine), "salao")
    out = do(engine, state, "go", "exit:balcao")
    assert out.state.location == "balcao"
    assert out.state.stats.temperature < 80
