# Agente: Backend

## 1. Responsabilidade
FastAPI, serviço de partidas, persistência (SQLAlchemy/Alembic), segurança HTTP.

## 2. Contexto necessário
`backend/caneca/{main.py,config.py,api/,services/,persistence/}`, `docs/architecture/data-model.md`, `docs/security/threat-model.md`.

## 3. Objetivos
- Cada turno: um commit com verificação de versão; narração gravada depois.
- Erros com código estável (`{"error": {"code", "detail"}}`) mapeado no i18n do cliente.
- Banco acessado em thread; nada bloqueante no loop durante o streaming.

## 4. Limites de atuação
Não altera regras do motor (`game/`) nem prompts (`ai/prompts.py`) sem o responsável. Não expõe segredos em respostas ou logs.

## 5. Critérios de aceitação
- Testes de API para toda rota/erro novo.
- Migração Alembic testada em banco novo e em banco existente (com backup automático).
- `ruff` e `mypy` sem erros nos arquivos tocados.

## 6. Dependências entre módulos
`services/games.py` usa `game.engine`, `ai.*`, `memory.context`, `persistence.*`, `api.views`. `api/routes.py` só chama o serviço.

## 7. Validação
```bash
cd backend
uv run pytest tests/test_api.py -q
uv run ruff check caneca && uv run mypy caneca
CANECA_DATA_DIR=/tmp/cq uv run caneca-server & curl -s 127.0.0.1:8765/api/health
```
