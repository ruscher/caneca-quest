# Capítulo 1 — O Despertar (Cafeteria Esquecida)

Arquivo de conteúdo: `backend/caneca/game/content/10-cafeteria.yaml`. Início: `mesa_principal`, 21:40, chuva.

## Locais

| id | Nome | Destaques |
|---|---|---|
| `mesa_principal` | Mesa perto da janela | Início. Jornal velho (manchete do fechamento), colherzinha adormecida, vidro com Noir do lado de fora (vista para `parapeito`). Torrão de açúcar e guardanapo. |
| `salao` | Salão do café | Hub. Quadro da inauguração (1979), aquecedor frio, botão dourado. |
| `balcao` | Balcão | Dona Doce, caixa registradora (moeda antiga), cardápio de giz. |
| `prateleiras` | Prateleiras altas | Sintonia (a voz), foto de Ilda. |
| `cozinha` | Cozinha | Velho Moedor, fogão (fonte de calor até 86 °C), máquina de café (reabastece uma vez), portinhola para o beco, sardinha. |
| `deposito` | Depósito | Sacos de café (chave de latão escondida), barbante, porta do porão trancada. |
| `porao` | Porão (11 °C) | Rato Bigode e seu tesouro (engrenagem dourada, saquinho de torrões), caixa de lembranças (diário de Ilda, mapa do bairro). |
| `janela` | Peitoril da janela | Trinco; ao abrir, Noir entra e a saída para o `parapeito` é liberada. |
| `porta_entrada` | Porta de entrada | Maçaneta alta (abre com o barbante), fresta. |

## Missões

- **`q_despertar` (principal)** — objetivos opcionais `descobrir_voz` e `segredo_ilda`; obrigatório `sair_cafeteria`. Ao entrar na cidade conclui com desfecho `com_respostas`, `meias_respostas` ou `sem_respostas`.
- **`q_doce`** — recuperar os torrões de Dona Doce com o Rato Bigode e devolvê-los (consolo opcional com o torrão da mesa).
- **`q_moedor`** — recuperar a engrenagem dourada e levá-la ao Moedor (ele a devolve para a floresta).
- **`q_noir`** — dar a sardinha a Noir, como Ilda fazia → Noir vira companheiro (`companion:noir`).
- **`q_reconciliacao`** (iniciada aqui) — o Moedor entrega o `bilhete_moedor` para o Bule.

## Caminhos e soluções

**Descer da mesa:** pela perna da cadeira (coragem CD 10), pulando (coragem CD 12, dano se falhar) ou usando o guardanapo como corda (sem teste, consome o guardanapo).

**A voz misteriosa:** gritar, escutar/investigar a voz, perguntar a Noir; ela vem das prateleiras. Falar com Sintonia sobre "por que estou viva" cumpre `descobrir_voz`.

**O segredo de Ilda:** ler o diário no porão, ouvir o Moedor (rel ≥ 20) ou Noir (rel ≥ 50); no capítulo 2 também vale ver Ilda pela janela da casa amarela, e no 3 o enigma do Livro.

**Porão:** Dona Doce conta da chave no saco de café → revistar sacos → usar a chave na porta.

**Rato Bigode:** troca 1 objeto brilhante (botão dourado do salão ou moeda antiga da registradora) por 1 peça (engrenagem primeiro, depois torrões). Alternativa hostil: assustá-lo (derramar café/gritar/atacar, coragem CD 12) para tomar os torrões — ele lembra e fica inimigo (rel −40).

**Moedor:** derramar café nele o emociona (+30, ensina resistência térmica); com rel suficiente conta de Ilda, do truque da porta e da briga com o Bule.

**Três saídas para a cidade:**
1. **Janela:** girar o trinco (coragem CD 11) → parapeito → saltar à calçada (coragem CD 12).
2. **Portinhola:** empurrar com coragem (CD 14), pedir a Noir que a segure (rel ≥ 30, Noir na cozinha) ou montar em Noir (rel ≥ 50) direto para a calçada.
3. **Porta da frente:** laçar a maçaneta com o barbante (criatividade CD 10; dica do Moedor).

Noir chega à cozinha se a jogadora pedir que entre (tópico `noir_entrar`) ou entra pela janela quando ela é aberta.
