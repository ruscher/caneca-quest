# Agente: Engenharia de IA

## 1. Responsabilidade
Provedores, prompts, refinamento de intenção, streaming, memória, resumos, segurança de saída.

## 2. Contexto necessário
`backend/caneca/ai/*`, `backend/caneca/memory/context.py`, `services/games.py::_play_turn`, `docs/ai/*.md`, `tests/test_ai.py`, `tests/fake_llm.py`.

## 3. Objetivos
- Narração coerente com o RESULTADO OFICIAL, no idioma e tom escolhidos, sem repetir aberturas.
- Contexto eficiente (orçamento por `context_tokens`), memória relevante, NPCs consistentes.
- Falhas sempre degradam para o texto do motor.

## 4. Limites de atuação
A IA nunca altera estado. Não remova a validação de candidatos nem o saneamento. Não presuma modelos instalados. Não envie dados para nuvem sem consentimento.

## 5. Critérios de aceitação
- Testes com fakes de protocolo para cada provedor e caminho de erro.
- Prompt continua separando instruções de dados (teste de tags forjadas).
- Medição real (latência/tokens) registrada ao trocar prompts ou modelos padrão — sem números inventados.

## 6. Dependências entre módulos
`prompts.py` lê `game.engine`/`mechanics` (somente leitura) e `memory.context`. `orchestrator.py` usa `providers`. `services/games.py` decide quando chamar.

## 7. Validação
```bash
cd backend && uv run pytest tests/test_ai.py -q
# Com Ollama real:
ollama list && curl -s 127.0.0.1:8765/api/ai/status?provider=ollama
```
