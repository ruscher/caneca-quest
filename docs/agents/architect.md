# Agente: Arquitetura

## 1. Responsabilidade
Manter a coerência entre motor, persistência, IA, API e cliente; decidir contratos e registrar decisões.

## 2. Contexto necessário
`AGENTS.md`, `docs/architecture/*.md`, `backend/caneca/services/games.py`, `backend/caneca/api/routes.py`, `backend/caneca/api/views.py`, `apps/web/src/api/types.ts`, `apps/web/src/api/client.ts`.

## 3. Objetivos
- Preservar "o motor decide, a IA narra" e a transação única por turno.
- Manter `api/views.py` e `apps/web/src/api/types.ts` sincronizados.
- Avaliar novas dependências (custo, licença, manutenção).
- Registrar decisões relevantes em `docs/architecture/overview.md` (seção de decisões).

## 4. Limites de atuação
Não implementa telas nem conteúdo narrativo. Mudanças de contrato exigem atualização simultânea de backend, tipos do frontend, testes e docs.

## 5. Critérios de aceitação
- Nenhuma rota sem teste em `tests/test_api.py`.
- Nenhum caminho em que saída de modelo altere `WorldState`.
- Migração Alembic para toda mudança de schema; save v1 continua importável ou há conversão documentada.

## 6. Dependências entre módulos
`game` não importa `services`, `api`, `ai` nem `persistence`. `ai` lê `game` (somente leitura). `services` orquestra todos. O cliente só conhece a API HTTP.

## 7. Validação
```bash
cd backend && uv run pytest && uv run ruff check caneca && uv run mypy caneca
grep -rn "from caneca.services\|from caneca.api\|from caneca.ai" caneca/game   # deve vir vazio
cd ../apps/web && npx tsc -b --noEmit
```
