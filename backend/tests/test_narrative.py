"""Narrative continuity: the world remembers, and Chapter 1/2 can be solved several ways."""

from __future__ import annotations

from helpers import do, fresh, say, until

from caneca.ai.prompts import build_narration_prompt
from caneca.game.engine import Engine
from caneca.game.mechanics import Mutator
from caneca.game.state import INVENTORY, WorldState
from caneca.memory.context import RecentTurn, budget_for, select_memory


def at(state: WorldState) -> str:
    return state.location


# ---------------------------------------------------------------- the key scenario
def test_key_stays_found_and_the_world_remembers(engine: Engine):
    s = fresh(engine, location="balcao", seed="chave")
    s = say(engine, s, "perguntar a dona doce sobre os torrões").state
    assert "chave_no_saco" in s.npcs["dona_doce"].memories

    s = say(engine, s, "passar pelo passa-pratos para a cozinha").state
    s = say(engine, s, "entrar no depósito").state
    assert at(s) == "deposito"
    # 1-2. Find the key and keep it.
    out = say(engine, s, "revistar os sacos de café")
    s = out.state
    assert s.item_locations["chave_latao"] == INVENTORY
    # 3-4. Leave and come back.
    s = say(engine, s, "voltar para a cozinha").state
    assert at(s) == "cozinha"
    s = say(engine, s, "entrar no depósito").state
    assert at(s) == "deposito"
    # 5-6. Still carried, not back in the sack, and the search can't be repeated.
    assert s.item_locations["chave_latao"] == INVENTORY
    assert "chave_latao" not in s.items_at("deposito")
    again = say(engine, s, "revistar os sacos de café")
    assert "item_gained" not in [e.kind for e in again.events]
    assert again.state.inventory().count("chave_latao") == 1
    s = again.state

    # 7. The NPC still recognizes what she told us.
    s = say(engine, s, "voltar para a cozinha").state
    s = say(engine, s, "subir pelo passa-pratos até o balcão").state
    assert at(s) == "balcao"
    out = say(engine, s, "falar com dona doce sobre a chave")
    assert out.dialogue_npc == "dona_doce"
    assert "chave_no_saco" in out.state.npcs["dona_doce"].memories

    # 8. The narrator receives the authoritative inventory and the recorded facts.
    memory = select_memory(
        out.state,
        "pt-BR",
        {"balcao", "dona_doce"},
        "falar com dona doce sobre a chave",
        [RecentTurn(1, "revistar os sacos", "Você encontra uma chave.")],
        "",
        budget_for(4096, 280),
        npc_id="dona_doce",
    )
    prompt = build_narration_prompt(engine, out.state, out, memory, [])
    assert "INVENTÁRIO: chave de latão" in prompt.user
    assert "a chave do porão está escondida num saco de café" in prompt.user
    assert "Lembra-se de" in prompt.user


# ---------------------------------------------------------------- chapter 1 exits
def test_exit_by_cat_flap_with_noir(engine: Engine):
    s = fresh(engine, location="mesa_principal", seed="portinhola")
    s = say(engine, s, "conversar com o gato").state
    s = say(engine, s, "pedir para o gato entrar pela cozinha", "noir").state
    assert s.npcs["noir"].location == "cozinha"
    s = until(engine, s, "descer pela cadeira", lambda x: x.location == "salao")
    s = say(engine, s, "ir para a cozinha").state
    assert at(s) == "cozinha"
    s = say(engine, s, "pegar a sardinha").state
    s = say(engine, s, "dar a sardinha para o gato").state
    assert "companion:noir" in s.flags and s.npcs["noir"].relationship >= 30
    assert s.quests["q_noir"].status == "completed"
    s = say(engine, s, "pedir ao gato para segurar a portinhola").state
    assert "portinhola_aberta" in s.flags
    s = say(engine, s, "sair pela portinhola").state
    assert at(s) == "beco"
    assert s.npcs["noir"].location == "beco", "Noir follows as a companion"
    assert s.quests["q_despertar"].outcome == "sem_respostas"
    assert s.chapter == 2


def test_exit_by_window_after_meeting_the_radio(engine: Engine):
    s = fresh(engine, location="mesa_principal", seed="janela")
    s = until(engine, s, "descer pela cadeira", lambda x: x.location == "salao")
    s = say(engine, s, "atravessar o salão até o balcão").state
    s = until(engine, s, "escalar as prateleiras", lambda x: x.location == "prateleiras")
    s = say(engine, s, "falar com o rádio").state
    s = say(engine, s, "por que estou viva?", "sintonia").state
    assert "descobrir_voz" in s.quests["q_despertar"].done
    s = until(engine, s, "descer de volta ao balcão", lambda x: x.location == "balcao")
    s = say(engine, s, "descer para o salão").state
    s = until(engine, s, "subir pelo aquecedor até a janela", lambda x: x.location == "janela")
    s = until(engine, s, "girar o trinco da janela", lambda x: "janela_aberta" in x.flags)
    assert s.npcs["noir"].location == "janela", "the cat comes in from the rain"
    s = say(engine, s, "sair pela janela aberta").state
    assert at(s) == "parapeito"
    assert s.quests["q_despertar"].outcome == "meias_respostas"
    s = until(engine, s, "saltar do parapeito para a calçada", lambda x: x.location == "calcada")
    assert s.chapter == 2


def test_exit_by_string_on_the_doorknob_with_all_answers(engine: Engine):
    s = fresh(engine, location="cozinha", seed="porta")
    s = say(engine, s, "entrar no depósito").state
    s = say(engine, s, "pegar o barbante").state
    assert s.item_locations["barbante"] == INVENTORY
    s = say(engine, s, "voltar para a cozinha").state
    s = say(engine, s, "voltar ao salão").state
    s = say(engine, s, "ir até a porta de entrada").state
    assert at(s) == "porta_entrada"
    mut = Mutator(engine.world, s)  # answers found earlier in this hypothetical run
    mut.complete_objective("q_despertar.descobrir_voz")
    mut.complete_objective("q_despertar.segredo_ilda")
    s = until(engine, s, "usar o barbante na maçaneta", lambda x: "porta_aberta" in x.flags)
    s = say(engine, s, "sair pela porta para a calçada").state
    assert at(s) == "calcada"
    assert s.quests["q_despertar"].outcome == "com_respostas"
    assert s.quests["q_cidade"].status == "active"


def test_leaving_without_meeting_anyone_completes_chapter_once(engine: Engine):
    s = fresh(engine, location="cozinha")
    s.flags.append("portinhola_aberta")
    s = say(engine, s, "sair pela portinhola").state
    xp = s.stats.xp
    s.flags.append("lata_liberou")
    s = say(engine, s, "seguir pelo beco até a calçada").state
    assert at(s) == "calcada"
    assert s.quests["q_despertar"].outcome == "sem_respostas"
    assert s.stats.xp == xp + 10, "only the new-location xp; the quest isn't rewarded twice"


# ---------------------------------------------------------------- city puzzles
def test_puddle_by_spilling_coffee_to_float(engine: Engine):
    s = fresh(engine, location="poca_oceano", seed="poca")
    out = say(engine, s, "atravessar a poça até o bueiro")
    assert at(out.state) == "poca_oceano" and out.success is False
    s = out.state
    while "buoyant" not in s.statuses:
        s = say(engine, s, "derramar um pouco de café").state
    s = until(engine, s, "atravessar a poça até o bueiro", lambda x: x.location == "bueiro")
    assert at(s) == "bueiro"


def test_puddle_with_bottle_cap_boat(engine: Engine):
    s = fresh(engine, location="lixeira", seed="barco")
    s = say(engine, s, "pegar a tampinha").state
    s = say(engine, s, "pegar o palito").state
    s = say(engine, s, "combinar a tampinha com o palito").state
    assert s.item_locations["barquinho"] == INVENTORY
    assert s.item_locations["tampinha"] != INVENTORY
    s.location = "poca_oceano"
    assert s.stats.coffee > 40
    s = until(engine, s, "navegar até o bueiro", lambda x: x.location == "bueiro")
    assert at(s) == "bueiro"


def test_secret_tunnel_appears_only_when_known(engine: Engine):
    s = fresh(engine, location="bueiro")
    assert all(ex.to != "orla" for ex in engine.visible_exits(s))
    s.flags.append("bueiro_revelado")
    assert any(ex.to == "orla" for ex in engine.visible_exits(s))


def test_crossing_by_waiting_for_the_light(engine: Engine):
    s = fresh(engine, location="cruzamento")
    s = say(engine, s, "esperar o sinal fechar").state
    assert "sinal_fechado" in s.flags
    out = say(engine, s, "atravessar a rua")
    assert at(out.state) == "jardim"
    assert out.check is None, "crossing on red needs no luck"
    assert "atravessar" in out.state.quests["q_cidade"].done


def test_crossing_with_zeca(engine: Engine):
    s = fresh(engine, location="calcada")
    s = say(engine, s, "falar com o pombo").state
    s.item_locations["casca_pao"] = INVENTORY
    s = say(engine, s, "dar a casca de pão para o zeca").state
    assert s.npcs["pombo_zeca"].location == "cruzamento"
    assert s.quests["q_zeca"].outcome == "pao"
    s = say(engine, s, "seguir até o cruzamento").state
    s = say(engine, s, "pedir ao zeca para voar comigo", "pombo_zeca").state
    assert at(s) == "jardim"


def test_crossing_riding_noir(engine: Engine):
    s = fresh(engine, location="cruzamento")
    s.npcs["noir"].location = "cruzamento"
    s.npcs["noir"].relationship = 60
    s.flags.append("companion:noir")
    s = say(engine, s, "montar no gato").state
    assert at(s) == "jardim"
    assert "cat_rider" in s.achievements
    assert s.npcs["noir"].location == "jardim"


def test_ferrugem_toll_alternatives(engine: Engine):
    base = fresh(engine, location="beco", seed="lata")
    blocked = say(engine, base, "seguir pelo beco até a calçada")
    assert at(blocked.state) == "beco"

    paid = base.model_copy(deep=True)
    paid.item_locations["tampinha"] = INVENTORY
    paid = say(engine, paid, "dar a tampinha para a lata").state
    assert paid.quests["q_lata"].outcome == "pedagio"
    assert say(engine, paid, "seguir pelo beco até a calçada").state.location == "calcada"

    respect = base.model_copy(deep=True)
    respect.flags.append("sabe_segredo_lata")
    respect = say(engine, respect, "dizer ao ferrugem que ele não é lixo").state
    assert respect.quests["q_lata"].outcome == "respeito"
    assert "bueiro_revelado" in respect.flags

    brave = base.model_copy(deep=True)
    brave.stats.courage = 90
    brave = until(engine, brave, "encarar o ferrugem", lambda x: "lata_liberou" in x.flags)
    assert brave.quests["q_lata"].outcome == "coragem"

    cat = base.model_copy(deep=True)
    cat.npcs["noir"].location = "beco"
    cat = do(engine, cat, "talk", "lata_ferrugem").state
    assert cat.quests["q_lata"].outcome == "noir"


def test_hedge_path_to_the_forest(engine: Engine):
    s = fresh(engine, location="jardim")
    assert all(ex.to != "orla" for ex in engine.visible_exits(s))
    s.item_locations["mapa_cidade"] = INVENTORY
    s = say(engine, s, "ler o mapa").state
    assert "sabe_do_bosque" in s.flags
    s = say(engine, s, "passar pelo buraco na cerca").state
    assert at(s) == "orla"
    assert s.chapter == 3
