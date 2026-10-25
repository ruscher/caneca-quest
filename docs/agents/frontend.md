# Agente: Frontend

## 1. Responsabilidade
Interface React/TypeScript em `apps/web`: telas, componentes, estado, comunicação com a API, PWA.

## 2. Contexto necessário
`apps/web/src/{App.tsx,store/,api/,screens/,components/,i18n/,styles/index.css}`, `docs/design/*.md`, `apps/web/vite.config.ts`.

## 3. Objetivos
- Interface fluida durante o streaming (nunca bloquear entrada/cancelamento).
- Responsividade sem rolagem horizontal de página; alvos ≥ 44 px.
- Toda string via `useT()`; chaves novas em `pt-BR.ts` e `en.ts`.
- Bundle enxuto (hoje ≈ 110 KB gzip de JS).

## 4. Limites de atuação
Não muda regras de jogo nem contratos da API sem o backend. Não usa `dangerouslySetInnerHTML`. Não adiciona bibliotecas de UI/animação sem justificativa.

## 5. Critérios de aceitação
- `tsc` e ESLint (incl. `react-hooks/set-state-in-effect`) sem erros.
- Testes Vitest para lógica nova (parsers, store, componentes com interação).
- Funciona em 1440, 820 e 390 px nos dois temas, com teclado.

## 6. Dependências entre módulos
`api/types.ts` espelha `backend/caneca/api/views.py`. `store/game.ts` depende de `api/client.ts`. Componentes leem estado via Zustand; preferências em `store/prefs.ts` (localStorage `caneca-prefs`, lida também por `public/theme-init.js`).

## 7. Validação
```bash
cd apps/web
npx tsc -b --noEmit && npx eslint . && npx vitest run && npx vite build
npx playwright test        # com o backend rodando
```
