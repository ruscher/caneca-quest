# Plano de testes

## Níveis e estado atual

| Nível | Ferramenta | Local | Estado |
|---|---|---|---|
| Unidade + integração (backend) | pytest | `backend/tests/` | implementado |
| Conteúdo (validação de referências) | carregador do mundo | `game/world.py` (falha na importação) | implementado |
| Unidade/componentes (frontend) | Vitest + Testing Library + jsdom | `apps/web/src/**/*.test.ts(x)` | implementado (94 testes) |
| E2E | Playwright (+ `@axe-core/playwright`) contra backend real + build | `apps/web/e2e/` | implementado (11 cenários: desktop e Pixel 7) |
| Desktop | execução real do binário Tauri | manual (ver abaixo) | verificado no Linux |
| Desempenho | medições reais | `docs/testing/performance.md` | ver documento próprio |
| CI | GitHub Actions | `.github/workflows/ci.yml` | configurado (não executado neste ambiente) |

## Backend — o que cada arquivo cobre

- `tests/conftest.py` — app com diretório de dados temporário, rate limit alto, fixtures `engine`, `new_state`, `client`, `game` (semente fixa) e helper `play` (turno não-streaming).
- `tests/test_api.py` — saúde e metadados; criação com view completa; turno de introdução no histórico; turno offline atualiza estado e histórico; intenção de sugestão; entidade inexistente rejeitada; conflito por `expected_turn` (409); validação (vazio, > 500, campo extra); 404; **injeção de prompt sem efeito**; formato SSE (`outcome` … `done`); diário e memórias (quem sabe cada fato); checkpoint: restaurar volta o estado, apaga turnos posteriores e guarda cópia de segurança; exportar/importar ida e volta; **importação adulterada recusada sem criar partida**; renomear/excluir; troca de idioma re-renderiza histórico; chaves de API nunca vazam; limite de corpo (413).
- `tests/test_ai.py` — Ollama: status/modelos, streaming e uso de tokens, erros tipados, serviço inacessível; OpenAI-compatível: streaming, uso, chave recusada; Anthropic: `system` separado, uso; URL inválida; filtro `<think>` entre pedaços; limpeza de markdown/menus e rejeição de recusas; pela API: status, narração em streaming gravada com `source=ai` e prompt contendo regras + ação delimitada; **falha do provedor → texto do motor sem corromper o save**; saída inválida substituída; tags forjadas pela jogadora não escapam do bloco; refinamento de intenção aceito; **intenção inventada pela IA ignorada**; nuvem exige consentimento; cancelamento sem turno ativo.
- `tests/test_forest_story.py` — chegada à floresta, névoa bloqueando a torre, duas formas de convencer Lume, enigma do Livro em texto livre, reconciliação Moedor/Bule, troca com Marina, os três finais (inclusive com a engrenagem alternativa), nada acontece depois do fim, caso sem engrenagem.
- `tests/fake_llm.py` — servidores simulados fiéis aos protocolos (NDJSON do Ollama, SSE OpenAI e Anthropic).
- `tests/test_rules.py`, `test_parser.py`, `test_engine.py`, `test_narrative.py`, `test_memory.py`, `test_persistence.py` — regras de atributos, interpretador pt-BR/en, motor, cenários narrativos (inclusive o da chave e as três saídas do café), memória e persistência/concorrência/importação. Detalhes no topo de cada arquivo.
- `tests/test_watchdog.py` — o sidecar percebe quando o processo pai morre.

## Frontend — o que cada arquivo cobre

- `src/api/sse.test.ts` — parser SSE com eventos partidos em pedaços arbitrários, CRLF, comentários, `ReadableStream`.
- `src/i18n/i18n.test.ts` — pt-BR e en com as mesmas chaves, sem textos vazios, mesmos placeholders; interpolação e tempo relativo.
- `src/components/game/narration.test.ts` — separação de falas (travessão em pt-BR, aspas em en, travessões parentéticos ficam como narração).
- `src/styles/contrast.test.ts` — contraste WCAG AA de todos os pares de tokens nos dois temas.
- `src/store/game.test.ts` — turno em streaming (outcome → deltas → done), envio de intenção de sugestão, entrada vazia/concorrente, recusa do servidor, cancelamento mantendo o texto oficial, aviso de IA.
- `src/components/components.test.tsx` — campo de ação (Enter, vazio, histórico ↑, sugestões, interromper), abas WAI-ARIA, medidores com valor textual, switch, retrato com rachaduras.

## E2E (`apps/web/e2e/`)

- `game.spec.ts` — primeira aventura com persistência após recarregar; capítulo 1 concluído pela porta com o barbante até o capítulo 2; pontos salvos e restauração; uso só com teclado; falha de rede; tema escuro persistido; Ollama indisponível reportado; axe (WCAG 2.2 AA) nos temas claro e escuro.
- `mobile.spec.ts` — Pixel 7: sem rolagem horizontal, campo de ação visível, painéis em folhas, axe, alvos de toque ≥ 40 px.
- `screenshots.spec.ts` — gera as imagens de `docs/screenshots/` a partir do app real.

## Desktop (verificação manual feita)

1. `npm run sidecar -w @caneca/desktop` e `npx tauri build` em `apps/desktop`.
2. Abrir o binário: o log mostra `GET /api/games` 200 vindo da UI; `curl` sem token na porta do sidecar → 401.
3. `kill -9` no app: o sidecar registra "processo … encerrado; desligando o servidor" e não sobra processo.

## Cenários narrativos obrigatórios

Cobrir com `Engine.resolve` e estado determinístico:
1. Pegar a chave → guardar → sair → voltar: a chave segue no inventário e não reaparece no local (invariante `item_locations`).
2. NPC presente lembra do fato (`npc.memories`); NPC ausente não.
3. Relação muda o comportamento (saudações/tópicos por condição de `rel`).
4. Desfechos alternativos de missão (`q_despertar` com/meias/sem respostas; `q_lata` por pedágio, coragem, respeito ou Noir).
5. Entradas malformadas e tentativas de manipular instruções.

Todos estão cobertos por cenários dedicados em `tests/test_narrative.py`, `test_engine.py` e `test_parser.py`.

## Comandos

```bash
cd backend && uv run pytest                     # tudo
uv run pytest tests/test_ai.py -q               # só IA
uv run pytest --cov=caneca --cov-report=term    # cobertura
cd ../apps/web && npx tsc -b --noEmit && npx eslint . && npx vitest run
npm run build && npx playwright test --project desktop --project mobile   # E2E (sobe o backend sozinho)
npx playwright test --project screenshots                                  # regera as capturas
npx playwright test                              # E2E (backend em execução; ver config)
```

## Plano E2E (Playwright)

- Projetos: Chromium desktop 1440×900, tablet 820×1180, celular 390×844 (toque); temas claro e escuro via `colorScheme`.
- Fluxo: boas-vindas → criar caneca (4 etapas) → jogar em modo básico com texto livre e sugestões → recarregar a página e continuar → checkpoint e restauração → exportar/importar.
- Verificações: sem erros de console; sem rolagem horizontal da página; foco visível e navegação por teclado (Tab, setas nas abas, Esc, Alt+n); `axe` sem violações sérias/críticas em boas-vindas, criação e jogo, nos dois temas; campo vazio desativa "Agir"; texto longo limitado a 500; erro de rede mostra alerta.
- Capturas de tela reais para o README geradas pela própria suíte.

## Verificações manuais antes de uma versão

- Ollama real: listar modelos, testar, jogar 10 turnos, cancelar uma narração, desligar o serviço no meio (deve cair para o texto do motor).
- Leitor de tela (Orca/NVDA): anúncio da narração final, rótulos dos medidores e abas.
- Zoom 200% e tamanho de texto 150% sem perda de conteúdo.
- Instalar a PWA e abrir offline (interface carrega; o jogo exige o servidor local).
