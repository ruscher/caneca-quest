# Capítulo 3 — A Floresta dos Objetos Perdidos

Arquivo de conteúdo: `backend/caneca/game/content/30-floresta.yaml`. Testes: `backend/tests/test_forest_story.py`.

Ao entrar na `orla` pela primeira vez: `q_cidade.encontrar_floresta`, capítulo 3, conquista `forest_found`, início de `q_relogio`.

## Locais

| id | Nome | Destaques |
|---|---|---|
| `orla` | Orla da floresta | Lume escondida nas raízes; objetos à deriva; folha de prata. Volta ao `jardim`. |
| `clareira` | Clareira dos Achados | Mestra Colher; hub da floresta; parede de névoa ao norte (torre bloqueada até `lume_ilumina`). |
| `casa_bule` | Casa do Bule (24 °C) | Bule Bartolomeu; fogareiro (fonte de calor até 80 °C); xícaras desirmanadas. |
| `biblioteca` | Biblioteca do Tronco Oco | Livro Sem Título; toco de vela na mesa de leitura. |
| `lago_garrafas` | Lago das Garrafas (10 °C) | Marina e sua engrenagem de reserva. |
| `torre_relogio` | Torre do Relógio (6 °C) | Relógio Tic; os finais acontecem aqui. |

## Missões

- **`q_relogio` (principal, `O Relógio Parado`)** — opcionais `ouvir_colher`, `convencer_lume`, `chegar_torre`, `trazer_engrenagem`; obrigatório `reiniciar`. Desfechos: `caminho_de_casa`, `coracao_quente`, `engrenagem_fria`.
- **`q_lume`** — ajudar Lume a reencontrar a coragem (desfechos `vela` ou `coragem`). Lume vira companheira (`companion:lume`) e abre o caminho pela névoa.
- **`q_livro` (secreta)** — responder ao enigma do Livro (resposta: *lembrança/memória*). Recompensa: chave de corda e a revelação sobre Ilda; também cumpre `q_despertar.segredo_ilda` se ainda faltava.
- **`q_reconciliacao`** — entregar o recado do Moedor ao Bule → flag `bule_reconciliado`, conquista `peacemaker`.

## Como resolver

**Chegar à torre (Lume):**
1. Dar o **toco de vela** (biblioteca) a Lume; ou
2. Encorajá-la ("vamos juntas", "coragem") com rel ≥ 30, coragem ≥ 60, **ou** depois que a Mestra Colher pedir por ela (tópico `colher_lume`, disponível após ouvir sobre o Relógio).
3. Vapor (`steam_control`) perto dela aumenta a amizade (+15).

**A engrenagem:**
- **Engrenagem dourada** do café (Rato Bigode → Moedor devolve para a jornada); ou
- **Rota alternativa — engrenagem de maresia** de Marina: perguntar sobre o brilho metálico e trocá-la pelo mapa do bairro, pela pena do Zeca ou pela foto de Ilda; ou, com rel ≥ 25, contar a ela a sua aventura.

**Calor:** a mola precisa de café ≥ 25% e ≥ 50 °C. Aquecer-se no fogareiro do Bule; Bartolomeu reabastece a caneca (uma vez; até três vezes se reconciliado). A torre é gelada (6 °C) e um evento de geada pode esfriar a caneca.

**Opcional:** dar corda em Tic com a chave do Livro (ele recupera a lucidez); conversar com objetos à deriva com `object_speech`; percepção de vibrações aponta para a torre; entregar à Mestra Colher o recado da neta (precisa ter acordado a colherzinha no capítulo 1 com `object_speech`).

## Finais (prioridade decrescente)

| Interação | Final | Condições |
|---|---|---|
| `final_caminho_de_casa` | `homecoming` | engrenagem + ≥ 50 °C + café ≥ 25% + Noir rel ≥ 50 ou companheiro + `bule_reconciliado` |
| `final_coracao_quente` | `warm_heart` | engrenagem + ≥ 50 °C + café ≥ 25% |
| `final_engrenagem_fria` | `cold_gear` | engrenagem (café frio ou quase vazio) |
| `relogio_sem_engrenagem` | — | sem engrenagem: explica o que falta e aponta Marina |

Os finais quentes deixam o café em 5% (a caneca dá o próprio calor). Todos concluem `q_relogio` e concedem `clock_restarted`. Comandos que disparam: "usar a engrenagem no relógio", "derramar café no relógio" ou a sugestão contextual.
