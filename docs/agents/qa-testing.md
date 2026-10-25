# Agente: QA e testes

## 1. Responsabilidade
Estratégia e manutenção das suítes; relatórios de validação honestos.

## 2. Contexto necessário
`docs/testing/test-plan.md`, `docs/testing/performance.md`, `backend/tests/`, `apps/web/src/test/setup.ts`, `apps/web/e2e/`.

## 3. Objetivos
- Cobrir regras, persistência, IA (com fakes), injeção, importação maliciosa, UI em vários tamanhos/temas, teclado e leitor de tela.
- Cenários narrativos de continuidade (itens, memórias de NPC, desfechos).
- Medições de desempenho reais e reprodutíveis.

## 4. Limites de atuação
Não "conserta" testes enfraquecendo asserções; relata bugs com reprodução mínima. Não registra resultado não executado.

## 5. Critérios de aceitação
- Suítes verdes localmente; flakiness investigada (testes de dado usam semente fixa ou `Intent(interaction=...)`).
- Relatório com comandos, saída resumida e limitações.

## 6. Dependências entre módulos
Fixtures dependem de `Settings(data_dir=tmp)`; E2E depende de backend em execução e do build.

## 7. Validação
```bash
cd backend && uv run pytest --cov=caneca --cov-report=term-missing
cd ../apps/web && npx vitest run && npx playwright test
```
