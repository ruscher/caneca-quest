# Agente: Game design

## 1. Responsabilidade
Regras e balanceamento: atributos, testes, custos, habilidades, progressão, dificuldades, verbos e handlers padrão.

## 2. Contexto necessário
`backend/caneca/game/{rules.py,engine.py,mechanics.py,content_schema.py}`, `docs/architecture/game-engine.md`, conteúdo YAML.

## 3. Objetivos
- Regras explícitas e testáveis; números em `rules.BALANCE` e tabelas de perfil.
- Escolhas com consequências reais; resultados previsíveis em condições equivalentes (RNG com semente).
- Modo História generoso, Sobrevivência exigente, Aventura equilibrado.

## 4. Limites de atuação
Não escreve prosa final (narrative design) nem mexe em prompts. Novas chaves de condição/efeito exigem atualização de `content_schema.py`, `mechanics.py`, validação em `world.py` e da doc.

## 5. Critérios de aceitação
- Teste unitário para cada regra alterada (ex.: resfriamento, dano por material, nível por XP).
- Todos os finais continuam alcançáveis (`tests/test_forest_story.py`).
- Documentação de números atualizada em `docs/architecture/game-engine.md`.

## 6. Dependências entre módulos
`rules` ← `mechanics` ← `engine`. O conteúdo depende do schema. A IA depende dos nomes de eventos (`ai/prompts.py::event_lines`).

## 7. Validação
```bash
cd backend && uv run pytest -q
uv run python -c "from caneca.game.world import get_world; get_world()"
```
