"""Chapter 3 — Forest of Lost Objects: deterministic story tests.

Each test sets up the minimum state needed (instead of replaying the whole adventure)
and drives the engine through ``Engine.interpret``/``Engine.resolve``, exactly as the
API does.
"""

from __future__ import annotations

import pytest

from caneca.game.engine import Engine, TurnOutcome
from caneca.game.parser import Intent
from caneca.game.state import INVENTORY, AdventureSettings, MugIdentity, WorldState
from caneca.game.world import get_world


@pytest.fixture(scope="module")
def engine() -> Engine:
    return Engine(get_world())


def new_state(engine: Engine, location: str = "orla") -> WorldState:
    state = engine.new_state(
        MugIdentity(name="Aurora", color="#f4efe6"),
        AdventureSettings(language="pt-BR"),
        seed="floresta-teste",
    )
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
) -> TurnOutcome:
    intent = Intent(
        verb=verb,
        target=target,
        item=item,
        interaction=interaction,  # type: ignore[arg-type]
        source="suggestion",
    )
    return engine.resolve(state, intent)


def kinds(outcome: TurnOutcome) -> list[str]:
    return [e.kind for e in outcome.events]


def test_arrival_from_garden_starts_chapter_three(engine: Engine) -> None:
    state = new_state(engine, "jardim")
    state.flags.append("sabe_do_bosque")
    out = do(engine, state, "go", "exit:orla")
    s = out.state
    assert s.location == "orla"
    assert s.chapter == 3
    assert "forest_found" in s.achievements
    assert s.quests["q_relogio"].status == "active"
    assert s.quests["q_cidade"].status == "completed"


def test_mist_blocks_tower_until_lume_shines(engine: Engine) -> None:
    state = new_state(engine, "clareira")
    out = say(engine, state, "ir para a torre do relógio")
    assert out.state.location == "clareira"
    assert out.success is False


def test_lume_relights_with_candle_and_follows(engine: Engine) -> None:
    state = new_state(engine, "orla")
    state.item_locations["toco_vela"] = INVENTORY
    out = say(engine, state, "dar a vela para a lanterna")
    s = out.state
    assert "lume_ilumina" in s.flags
    assert s.item_locations["toco_vela"] != INVENTORY
    assert s.quests["q_lume"].status == "completed"
    assert "convencer_lume" in s.quests["q_relogio"].done

    s = say(engine, s, "seguir a trilha até a clareira").state
    assert s.location == "clareira"
    assert s.npcs["lume"].location == "clareira"  # Lume is now a companion
    s = say(engine, s, "atravessar a névoa até a torre").state
    assert s.location == "torre_relogio"
    assert "chegar_torre" in s.quests["q_relogio"].done


def test_lume_relights_through_mistress_spoon_advice(engine: Engine) -> None:
    state = new_state(engine, "clareira")
    s = say(engine, state, "perguntar à colher sobre o relógio").state
    assert "ouvir_colher" in s.quests["q_relogio"].done
    s = say(engine, s, "pedir conselho sobre a lanterna lume", "mestra_colher").state
    assert "colher_pediu_lume" in s.flags
    s = say(engine, s, "voltar para a orla").state
    s = do(engine, s, "talk", "lume").state
    s = say(engine, s, "Lume, vamos juntas, você consegue!", "lume").state
    assert "lume_ilumina" in s.flags
    assert s.quests["q_lume"].outcome == "coragem"


def test_book_riddle_answered_in_free_text(engine: Engine) -> None:
    state = new_state(engine, "biblioteca")
    s = say(engine, state, "falar com o livro").state
    s = say(engine, s, "qual é o seu enigma?", "livro_sem_titulo").state
    assert "livro_enigma" in s.flags
    out = say(engine, s, "A resposta é a lembrança!", "livro_sem_titulo")
    s = out.state
    assert s.quests["q_livro"].status == "completed"
    assert s.item_locations["chave_corda"] == INVENTORY
    assert "lembrar_mantem_vivo" in s.facts
    # The Book witnessed the revelation and remembers it.
    assert "lembrar_mantem_vivo" in s.npcs["livro_sem_titulo"].memories


def test_teapot_reconciliation(engine: Engine) -> None:
    state = new_state(engine, "casa_bule")
    state.item_locations["bilhete_moedor"] = INVENTORY
    state.quest("q_reconciliacao").status = "active"
    out = say(engine, state, "entregar o recado ao bule")
    s = out.state
    assert "bule_reconciliado" in s.flags
    assert "peacemaker" in s.achievements
    assert s.quests["q_reconciliacao"].status == "completed"
    assert s.item_locations["bilhete_moedor"] != INVENTORY
    s = say(engine, s, "pode ensinar a curar rachaduras?", "bule_bartolomeu").state
    assert "crack_mending" in s.abilities


def test_marina_trades_spare_gear_for_a_map(engine: Engine) -> None:
    state = new_state(engine, "lago_garrafas")
    state.item_locations["mapa_cidade"] = INVENTORY
    s = say(engine, state, "perguntar à garrafa sobre o brilho metálico").state
    assert "marina_troca" in s.flags
    s = say(engine, s, "dar o mapa para a garrafa").state
    assert s.item_locations["engrenagem_maresia"] == INVENTORY
    assert s.item_locations["mapa_cidade"] != INVENTORY


def _at_tower_with_gear(engine: Engine, gear: str = "engrenagem_dourada") -> WorldState:
    state = new_state(engine, "torre_relogio")
    state.item_locations[gear] = INVENTORY
    state.flags.extend(["lume_ilumina", "companion:lume"])
    state.npcs["lume"].location = "torre_relogio"
    state.stats.temperature = 72
    state.stats.coffee = 60
    return state


def test_ending_homecoming(engine: Engine) -> None:
    state = _at_tower_with_gear(engine)
    state.flags.append("bule_reconciliado")
    state.npcs["noir"].relationship = 60
    out = say(engine, state, "derramar meu café quente no relógio")
    s = out.state
    assert s.ending == "homecoming"
    assert s.quests["q_relogio"].outcome == "caminho_de_casa"
    assert "clock_restarted" in s.achievements
    assert s.stats.coffee <= 5
    assert s.item_locations["engrenagem_dourada"] != INVENTORY
    assert "ending" in kinds(out)
    # A finished story accepts no further actions.
    after = say(engine, s, "olhar ao redor")
    assert after.meta and after.state.turn == s.turn


def test_ending_warm_heart_with_spare_gear(engine: Engine) -> None:
    state = _at_tower_with_gear(engine, "engrenagem_maresia")
    out = say(engine, state, "usar a engrenagem no relógio")
    assert out.state.ending == "warm_heart"
    assert out.state.quests["q_relogio"].outcome == "coracao_quente"
    assert out.state.item_locations["engrenagem_maresia"] != INVENTORY


def test_ending_cold_gear_when_coffee_is_cold(engine: Engine) -> None:
    state = _at_tower_with_gear(engine)
    state.stats.temperature = 30
    out = do(engine, state, "use", "relogio_tic", "engrenagem_dourada")
    assert out.state.ending == "cold_gear"
    assert out.state.quests["q_relogio"].outcome == "engrenagem_fria"


def test_clock_without_gear_explains_and_does_not_end(engine: Engine) -> None:
    state = _at_tower_with_gear(engine)
    state.item_locations["engrenagem_dourada"] = "npc:rato_bigode"
    out = say(engine, state, "derramar café no relógio")
    assert out.state.ending is None
    assert "sabe_engrenagem_marina" in out.state.flags
    assert out.state.quests["q_relogio"].status != "completed"


def test_every_ending_is_reachable_by_suggestion(engine: Engine) -> None:
    state = _at_tower_with_gear(engine)
    labels = {s.interaction for s in engine.suggestions(state)}
    assert "final_coracao_quente" in labels
