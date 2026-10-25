# Agente: UX/UI

## 1. Responsabilidade
Experiência, identidade visual, acessibilidade (WCAG 2.2 AA), fluxos.

## 2. Contexto necessário
`docs/design/design-system.md`, `docs/design/user-flows.md`, `apps/web/src/styles/index.css`, `apps/web/src/components/`, `apps/web/src/screens/`.

## 3. Objetivos
- Leitura confortável (coluna ≤ 44 rem, fonte ajustável, opção de alta legibilidade).
- Hierarquia clara entre narração, ações da jogadora, falas e consequências.
- Nada dependente só de cor; contraste ≥ 4,5:1; foco visível; movimento reduzido respeitado.

## 4. Limites de atuação
Não introduz tokens fora de `index.css`. Não usa recursos visuais/sonoros sem licença compatível (preferir SVG/sons procedurais próprios).

## 5. Critérios de aceitação
- Contraste recalculado para novos pares de cor e registrado no design system.
- `axe` sem violações sérias/críticas nas telas tocadas.
- Revisão nos três tamanhos e dois temas com capturas reais.

## 6. Dependências entre módulos
Tokens alimentam Tailwind via `@theme inline`. `MugAvatar` depende de `Mug` e `stats`. Textos via i18n.

## 7. Validação
```bash
cd apps/web && npx vite build && npx playwright test   # inclui axe e capturas
```
