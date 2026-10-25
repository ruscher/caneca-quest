# Agente: Narrative design

## 1. Responsabilidade
Mundo, personagens, diálogos, missões e finais em YAML; consistência de tom e lore.

## 2. Contexto necessário
`docs/narrative/world-bible.md`, `docs/narrative/chapter-0*.md`, `backend/caneca/game/content/*.yaml`, `content_schema.py`.

## 3. Objetivos
- Toda fala/descrição em pt-BR e en; caneca no feminino em português ("viva").
- Cada desafio com pelo menos duas soluções; missões com desfechos alternativos (`outcomes`, efeitos com `when`).
- Personagens só sabem o que viram (`fact` com `witnesses`, `knowledge`, `secrets` com `reveal_if`).

## 4. Limites de atuação
Não altera código Python. Se precisar de um novo tipo de condição/efeito, pede ao game design.

## 5. Critérios de aceitação
- Conteúdo carrega sem erros de referência.
- Interações sem alvo têm `keywords` quando competem no mesmo local.
- Playthrough de teste cobrindo o caminho novo.
- Docs de capítulo atualizadas.

## 6. Dependências entre módulos
Ids de locais, itens, NPCs, missões e finais são referenciados entre arquivos (`00-world`, `10-cafeteria`, `20-cidade`, `30-floresta`). Prompts usam `personality`, `voice`, `knowledge`, `background` dos NPCs.

## 7. Validação
```bash
cd backend && uv run python -c "from caneca.game.world import get_world; w=get_world(); print(len(w.locations), len(w.npcs))"
uv run pytest -q
```
