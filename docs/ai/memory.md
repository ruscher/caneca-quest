# Memória da IA

Código: `backend/caneca/memory/context.py`, uso em `services/games.py` e `ai/prompts.py`.

## Camadas

| Camada | Onde vive | Como entra no prompt |
|---|---|---|
| Imediata | tabela `turns` | últimos `memory_turns` turnos de ação: `[entrada] → narração` (narração cortada em 420 caracteres) |
| Episódica | tabela `journal` | alimenta o resumo incremental |
| Longo prazo | `WorldState.facts` | fatos ranqueados por relevância |
| Do mundo | o próprio `WorldState` | cena atual, inventário, condições, habilidades — sempre presente e autoritativo |
| Do personagem | `NpcState.memories` | fatos que o interlocutor presenciou ou soube; prioridade máxima no diálogo |
| Resumo | `games.summary` | resumo das partes antigas da jornada |

Fatos são criados por efeitos `fact` do conteúdo. Por padrão (`witnesses: present`), todo NPC presente na cena passa a lembrar do fato; NPCs ausentes não sabem — assim um personagem não "adivinha" o que não viu. Segredos de NPC só entram no prompt quando suas condições `reveal_if` valem.

## Orçamento de contexto

```
budget_chars = max(512, context_tokens − max_tokens_da_resposta − 1200) × 4 × 0,45
```

(4 caracteres ≈ 1 token; 1200 tokens reservados para instruções e cena; 45% do restante para memória.)

Ordem de preenchimento (para quando o orçamento acaba):
1. Resumo (até 30% do orçamento; se maior, mantém o final).
2. Memórias do interlocutor (mais recentes primeiro).
3. Turnos recentes (do mais novo ao mais antigo).
4. Fatos de longo prazo, por pontuação.

## Pontuação de fatos

```
score = 2·importância
      + 3·|tags ∩ entidades da cena|        (local, região, NPCs presentes, itens no local e no inventário)
      + 1,5 se o fato ocorreu no local atual
      + 0,8·|palavras (>3 letras) da ação ∩ palavras do fato|
      + 2 / (1 + idade_em_turnos/5)
```

Fatos que não cabem são contados em `dropped_facts` (diagnóstico).

## Resumos incrementais

A cada `summary_every` turnos (padrão 12): reúne entradas do diário desde o último resumo + até 8 turnos recentes. Com IA, o modelo reescreve o resumo anterior incorporando os novos fatos (≤ 120 palavras, conteúdo tratado como dado). Sem IA ou em falha, o resumo é a concatenação determinística, mantendo os últimos 1500 caracteres. Guardado em `games.summary` (máx. 4000) e copiado nos checkpoints.

## Por que ainda não há embeddings

- O mundo é autorado e marcado: tags de entidades e a cena atual já identificam o que é relevante com precisão.
- Uma partida típica tem dezenas de fatos, não milhares; a ordenação estruturada cabe em microssegundos.
- Embeddings exigiriam um modelo extra (disponível nem sempre no Ollama do usuário) e mais dependências.

Quando adicionar: se partidas longas passarem de algumas centenas de fatos/turnos relevantes, ou se o conteúdo procedural gerar fatos sem tags. Plano: indexar `facts` e turnos com o endpoint de embeddings do provedor, guardar vetores numa tabela SQLite, e **medir** (taxa de contradições em cenários de teste) antes de ativar por padrão.
