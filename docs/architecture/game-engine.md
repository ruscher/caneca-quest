# Motor de jogo

Código: `backend/caneca/game/`. O motor é puro: recebe `WorldState` + `Intent`, devolve `TurnOutcome` (novo estado, mensagens `LText`, eventos estruturados, teste de dados, sugestões). Não acessa rede nem banco.

## Pipeline de `Engine.resolve`

1. Copia profunda do estado; se a partida terminou, devolve só `game_over` (meta, sem novo turno).
2. `turn += 1`; RNG = `Random("{seed}:{turn}")` (e `"{seed}:{turn}:{salt}"` por teste).
3. `_dispatch`:
   - intenção marcada como injeção → mensagem fixa, nada muda;
   - `target`/`item` fora dos candidatos da cena → "não encontra isso aqui";
   - verbos meta (`inventory`, `status`, `help`) não passam tempo;
   - `look` com alvo vira `examine`;
   - tenta uma **interação** do conteúdo; senão, o handler padrão do verbo.
4. `_tick` (exceto meta): avança minutos, resfria, gasta energia, vaza café se rachada, decrementa recargas, aviso ao cruzar 40 °C, evento aleatório, derrota se integridade ≤ 0.
5. Recalcula condições derivadas, conquistas automáticas, sugestões.

## Intenções e interpretação

`Intent = {verb, target, item, raw, source (parser|suggestion|ai), confidence, interaction?, injection}`.

`parser.parse` (pt-BR e inglês): normaliza (minúsculas, sem acento), detecta verbo pela frase mais longa do léxico, ancora entidades nas palavras-chave dos **candidatos da cena** (itens no local e no inventário, detalhes visíveis, NPCs presentes e vistos de longe, saídas, habilidades, "self"), descarta acertos contidos em acertos maiores e mantém empates de mesmo trecho (o verbo decide o papel; `go` prefere saídas). Atalhos de uma letra (`i`, `l`, `x`, `z`, `?`). Sem verbo: NPC → `talk`, saída → `go`, item/detalhe → `examine`; sem entidade → `improvise` (confiança 0.2), ou `talk` com o interlocutor atual se o texto parecer fala (pergunta, exclamação, aspas). Padrões de injeção de prompt geram `injection=true`.

`Engine.interpret` acrescenta o contexto de conversa: se o parser deu `improvise` e o texto bate com um tópico do interlocutor, vira `talk`.

Verbos: `look, examine, go, take, drop, use, combine, talk, give, jump, hide, rest, spill, shout, listen, wait, warm, befriend, ride, attack, ability, inventory, status, help, improvise`.

## Correspondência de interações

Uma interação aplica-se quando:
- o verbo está em `verbs` e o local em `at` (se definido);
- `target` (se definido) está entre as menções da intenção;
- `item` (se definido) foi mencionado, **ou** está implícito: verbo `use`, item no inventário e a jogadora não nomeou outro item carregado;
- sem `target`/`item`, a intenção não menciona nada — exceto para verbos livres (`listen, wait, shout, spill, hide, jump, rest, improvise`);
- se há `keywords`, alguma aparece no texto (ignorado quando a interação é pedida pelo id explícito vindo de uma sugestão);
- todas as `conditions` valem.

Ordenação: `priority` desc, depois especificidade (alvo+item > um > nenhum). Interações `once` já feitas mostram `once_text` (se houver) ou são puladas. Com `check`, falha ou "parcial" aplicam `fail_text`/`fail_effects` (parcial = metade dos deltas de atributos); `once` só marca em sucesso.

## DSL de condições (`Condition`)

Todas as chaves presentes precisam valer (E lógico): `flag`, `not_flag`, `has_item`, `lacks_item`, `item_at: [item, onde]`, `at` (id ou lista), `visited`, `stat` + `gte`/`lte`, `rel` (NPC) + `gte`/`lte`, `counter` + `gte`/`lte`, `npc_at: [npc, local]`, `met`, `npc_remembers: [npc, fato]`, `quest` + `status` (padrão `active`), `objective: "missao.objetivo"`, `ability`, `level_gte`, `has_status`, `lacks_status`, `difficulty`, `chapter_gte`, `any: [...]`, `all: [...]`, `not: {...}`.

## DSL de efeitos (`Effect`)

`when: [condições]` torna o efeito inteiro condicional. As chaves aplicam-se nesta ordem:
`set_flag`, `clear_flag`, `give_item`, `take_item` (→ void), `place_item: [item, local|void]`, `stats` (deltas; dano de integridade escalado por dificuldade, material e traço `sturdy`), `set_stats`, `rel` (traço `charming` amplia ganhos em 20%), `npc_mood`, `npc_remembers`, `move_npc`, `unlock_exit` (`a>b`), `quest_start`, `objective` (inicia a missão se preciso; conclui sozinha se `auto_complete` e todos os obrigatórios feitos), `quest_complete: {id, outcome}` (XP + `rewards`), `quest_fail`, `learn`, `journal: {title, text}`, `fact: {id, text, importance, tags, witnesses: present|none}` (NPCs presentes passam a lembrar), `achievement`, `discover`, `reputation`, `counter`, `status_add`, `status_remove`, `minutes`, `xp`, `chapter` (só avança; gera entrada no diário e checkpoint automático), `move_player` (dispara `on_enter` do destino), `ending`.

## Testes de dados

`roll = d20` · `mod = modificador de atributo + bônus de condição + bônus da dificuldade + bônus situacionais` (habilidades, itens carregados, relação: `rel // 20 × peso`).
- Coragem/criatividade: `floor((v − 50) / 10)`; energia/integridade/temperatura: `floor((v − 50) / 15)`.
- Condições: quente +1, morna −1, fria −3, exausta −2, vazia −2 (criatividade), em pedaços −2; `advanced_balance` +1.
- Dificuldade: história +2, aventura 0, sobrevivência −1.
- Resultado: 20 natural ou total ≥ CD+5 → crítico; 1 natural → fracasso; total ≥ CD → sucesso; ≥ CD−3 → parcial; senão fracasso. Crítico e sucesso contam como sucesso.

## Atributos (valores em `rules.BALANCE`)

| Regra | Valor |
|---|---|
| Resfriamento (Newton) | `T = amb + (T − amb)·e^(−k·min)`, k = 0,01/min × multiplicadores (dificuldade 0,6/1,0/1,4; material; `thermal` ×0,85; `thermal_resistance` ×0,6) |
| Aquecer em fonte | +25 °C até o limite do local; ≥ 85 °C numa fonte ≥ 92 °C causa dano térmico 5 |
| Faixas | ≥ 92 superaquecida · ≥ 60 quente · < 40 morna · < 25 fria |
| Café | derramar −10%; ≤ 40% flutuante; 0% vazia |
| Energia | custos por ação × dificuldade × material (+20% se morna/fria); < 15 exausta; saídas com custo ≥ 6 exigem energia |
| Descanso | +30 × bônus da dificuldade (1,4/1,0/0,8), metade se fria; 20 min |
| Integridade | ≤ 50 rachada (vaza 1% de café por turno) · ≤ 20 em pedaços · 0 derrota; no modo História não cai abaixo de 5 |
| Capacidade | peso carregado ≤ 6/5/4 (história/aventura/sobrevivência) |
| XP | nível N exige `50·N·(N−1)`; subir de nível: energia cheia, +5 coragem e criatividade, habilidades com `auto_at_level` |
| XP fixo | novo local +10; combinação +5; improviso bem-sucedido +3 (até 10 vezes) |

Valores iniciais: 80 °C, 75% café, 95% integridade, 100% energia, 50 coragem/criatividade, ajustados por bebida e traços.

## Tempo

Cada ação custa minutos (interações/saídas definem; descansar 20, esperar 10). A hora exibida é `clock_start + minutes`. Nada depende do relógio real: partidas pausadas não sofrem.

## Eventos aleatórios

Depois de um turno sem deslocamento/conclusão de missão/final, se passaram ≥ 5 turnos do último evento e `rng < 0,12`, sorteia-se (por peso) um evento da região cujas condições valem e que não seja `once` já visto.

## Verbos padrão (sem interação)

`look` (descrição + resumo da cena), `examine` (item, NPC, detalhe, saída, "self"), `go` (condições/desbloqueio, energia, teste, `on_enter`), `take`/`drop` (capacidade, portabilidade), `use` (fonte de calor → aquecer; senão nada acontece), `combine` (receitas, ambos no inventário), `talk` (tópico por palavras-chave, ignorando o nome do NPC; saudação no primeiro encontro; senão fala casual), `befriend` (coragem vs. `befriend_dc`, +5, até 3 vezes), `give` (presença física; `likes` +15, neutro +3, `dislikes` −10 e recusa), `jump` (usa saída do tipo salto se houver), `hide` (criatividade CD 10, +4 com `camouflage`), `rest`, `spill`, `shout` (+1 coragem nas 3 primeiras), `listen` (sons do local), `wait`, `warm`, `ride` (só por interação), `attack` (dano próprio; relação −15), `ability` (custos, recarga, temperatura mínima, efeitos), `improvise` (criatividade CD 11).

## Companheiros

Flag `companion:<npc>` faz o NPC acompanhar a caneca a cada deslocamento a partir do mesmo local.

## Sugestões

Até 6, nesta ordem: interações com `suggest` disponíveis aqui (até 4, por prioridade, carregando o id explícito), conversar com NPCs (e um tópico novo com `label`), aquecer/descansar quando necessário, pegar um item, até 2 saídas (não visitadas primeiro), examinar um detalhe não descoberto, olhar ao redor.

## Conquistas automáticas

`first_friend` (relação ≥ 50), `best_friends` (≥ 80), `social_mug` (6 NPCs conhecidos), `explorer` (12 locais), `cartographer` (todos os locais não pseudo), `close_call` (0 < integridade ≤ 20), `seasoned` (nível 3). As demais vêm de efeitos do conteúdo.

## Capítulos e finais

Capítulo 1 (cafeteria) → 2 ao pisar na cidade (`parapeito`, `calcada` ou `beco`; `q_despertar` conclui com desfecho `com_respostas`, `meias_respostas` ou `sem_respostas`) → 3 ao chegar à `orla` da floresta. Finais definidos em `00-world.yaml` (`homecoming`, `warm_heart`, `cold_gear`) e disparados por interações na `torre_relogio` com prioridades decrescentes; derrota quando a integridade chega a 0. Ver `docs/narrative/`.
