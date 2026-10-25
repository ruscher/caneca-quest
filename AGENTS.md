# AGENTS.md — Guia para agentes e contribuidores

Este arquivo orienta qualquer agente de IA (ou pessoa) que vá trabalhar no **Caneca Quest — A Jornada de uma Caneca**. Leia-o antes de alterar o código. Especificações por papel estão em [`docs/agents/`](docs/agents/).

## 1. Visão do produto

RPG narrativo de texto em que a jogadora é uma caneca de café viva, vista da escala de um objeto pequeno. A jogadora escreve ações em linguagem natural (ou escolhe sugestões); um **motor de regras determinístico** decide o que acontece e uma **IA opcional** (Ollama local ou provedor em nuvem) narra o resultado. Sem IA, o jogo é completo com narrativa pré-escrita.

Princípio inegociável: **o motor decide, a IA narra.** Nenhuma saída de modelo altera estado de jogo.

## 2. Estrutura do repositório (real)

```text
caneca-quest/
├── AGENTS.md                 ← este arquivo
├── package.json              ← workspaces npm (apps/web, apps/desktop)
├── backend/                  ← Python 3.11+ / FastAPI / SQLite
│   ├── pyproject.toml        ← dependências (uv), ruff, mypy, pytest
│   ├── caneca/
│   │   ├── main.py           ← fábrica da app FastAPI + CLI `caneca-server`
│   │   ├── config.py         ← Settings (variáveis CANECA_*)
│   │   ├── api/              ← routes.py (REST+SSE), views.py (modelos de leitura), security.py (middleware)
│   │   ├── services/         ← games.py (pipeline de turno, saves, checkpoints), saves.py (export/import v1)
│   │   ├── game/             ← motor: content_schema, world (loader+validação), state, rules,
│   │   │   │                   mechanics (condições/efeitos), parser (intenções), engine, messages, i18n
│   │   │   └── content/      ← mundo em YAML: 00-world, 10-cafeteria, 20-cidade, 30-floresta
│   │   ├── ai/               ← config (AISettings, SecretStore), prompts, orchestrator, safety
│   │   │   └── providers/    ← base, ollama, cloud (OpenAI-compatível, Anthropic), http_common
│   │   ├── memory/           ← context.py (seleção de memória com orçamento)
│   │   └── persistence/      ← orm.py, db.py (sessões, migrações, backups), migrations/ (Alembic)
│   ├── scripts/bench.py      ← medições de desempenho (docs/testing/performance.md)
│   └── tests/                ← pytest (regras, parser, motor, narrativa, memória, persistência, API, IA, floresta)
├── apps/
│   ├── web/                  ← React 19 + TS 5.9 + Vite 8 + Tailwind 4 + Zustand (PWA)
│   │   ├── src/{api,audio,components/{game,ui},i18n,screens,speech,store,styles,test}
│   │   └── e2e/              ← Playwright (sobe o backend real com dados temporários)
│   └── desktop/src-tauri/    ← Tauri 2 (Rust): inicia o sidecar do backend e abre a UI
├── docs/                     ← arquitetura, IA, design, narrativa, segurança, testes, agentes, screenshots
├── scripts/build_sidecar.py  ← empacota o backend com PyInstaller para o desktop
└── .github/workflows/        ← ci.yml (lint, tipos, testes, build, E2E) e release.yml (instaladores)
```

## 3. Comandos de desenvolvimento

```bash
# Backend
cd backend
uv sync                                   # cria .venv e instala dependências
uv run caneca-server                      # API em http://127.0.0.1:8765 (dados em ~/.local/share/caneca-quest)
uv run caneca-server --static-dir ../apps/web/dist   # serve também a PWA compilada
uv run pytest                             # testes
uv run ruff check caneca && uv run ruff format --check caneca
uv run mypy caneca

# Frontend (na raiz do repositório)
npm install
npm run dev:web                           # Vite em :5173, proxy /api → 127.0.0.1:8765
npm run build:web                         # tsc -b + vite build → apps/web/dist
npm run test:web                          # Vitest
npm run lint:web                          # ESLint
npm run build:web && npm run e2e         # Playwright: sobe o backend sozinho (uv) com dados temporários

# Desktop (Linux: precisa de webkit2gtk-4.1; ver README)
npm run sidecar -w @caneca/desktop        # backend → apps/desktop/src-tauri/binaries/caneca-server-<triple>
cd apps/desktop && npx tauri build        # instaladores em src-tauri/target/release/bundle/
```

Variáveis úteis: `CANECA_DATA_DIR`, `CANECA_PORT`, `CANECA_STATIC_DIR`, `CANECA_API_TOKEN`, `CANECA_OLLAMA_URL`, `CANECA_OPENAI_API_KEY`, `CANECA_ANTHROPIC_API_KEY`, `CANECA_BACKEND_URL` (alvo do proxy do Vite).

## 4. Padrões de código

**Python**
- Tipagem completa; `mypy --strict` é o alvo. Modelos de dados são Pydantic com `extra="forbid"`.
- Ruff com as regras do `pyproject.toml` (E, F, W, I, B, UP, S, SIM, RUF, ASYNC), linha de 110 colunas.
- Só `game/mechanics.py` (`Mutator`) altera `WorldState`. Handlers do motor emitem `GameEvent`s; nada de mutação espalhada.
- Acesso a banco é síncrono e roda em threads (`anyio.to_thread`) a partir das rotas async. Toda escrita passa por `Database.session()` (commit/rollback automático).
- Texto ao jogador vindo do motor é sempre `LText` (`{"pt-BR": ..., "en": ...}`); a escolha de idioma acontece nas bordas (views, prompts).

**TypeScript/React**
- `strict`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`. Sem `any` implícito.
- ESLint com `typescript-eslint` e `eslint-plugin-react-hooks` (inclui `set-state-in-effect`: não chame `setState` sincronamente em efeitos — derive estado ou use callbacks de promessa/eventos).
- **Nenhuma string de interface fixa em componente.** Use `useT()` e chaves em `src/i18n/pt-BR.ts`; `en.ts` é tipado como `Dictionary` e precisa ter as mesmas chaves.
- Componentes acessíveis: rótulos, `aria-*`, alvos de toque ≥ 44 px, nada dependente só de cor.
- Estado global em Zustand (`store/game.ts`, `store/prefs.ts`); preferências persistem em `localStorage` via armazenamento tolerante a falhas.

## 5. Restrições técnicas

- O jogo deve funcionar **sem IA e sem rede** (modo básico).
- Não presumir modelo instalado no Ollama; a UI lista o que existe.
- Nada de chaves/segredos no repositório nem no frontend. Chaves ficam em variável de ambiente ou em `secrets.json` (0600) no diretório de dados.
- Provedores em nuvem só são usados com `cloud_consent = true`.
- Sem relógio real aplicando dano: o tempo é simulado por ação.
- Dependências novas exigem justificativa (tamanho, manutenção, licença).

## 6. Arquitetura de IA (resumo)

1. Texto livre → `Engine.interpret` (parser determinístico pt-BR/en + contexto de conversa).
2. Se a confiança < 0.6 e a IA estiver ativa, o modelo classifica a intenção em JSON Schema; o resultado **só é aceito se os ids existirem entre os candidatos da cena** (senão, mantém-se o parser).
3. `Engine.resolve` aplica regras e efeitos; o estado é gravado de forma transacional **antes** da narração.
4. A IA recebe instruções fixas de sistema + blocos de dados (cena, caneca, memória, personagem, ação da jogadora delimitada e sanitizada, RESULTADO OFICIAL) e narra em streaming.
5. A saída é limpa (`ai/safety.py`); se for inválida, vazia ou falhar, usa-se o texto do motor. O save nunca depende da IA.

Detalhes: [`docs/ai/providers.md`](docs/ai/providers.md), [`docs/ai/memory.md`](docs/ai/memory.md), [`docs/architecture/game-engine.md`](docs/architecture/game-engine.md).

## 7. Como adicionar conteúdo

O mundo é dado, não código. Edite/crie YAML em `backend/caneca/game/content/` seguindo `game/content_schema.py`:

- Locais (`locations`), itens, NPCs (com `greetings`, `topics`, `secrets`), `interactions`, `recipes`, `quests`, `abilities`, `events`, `achievements`, `endings`.
- Todo texto precisa de `pt-BR` **e** `en` (validado).
- O carregador (`game/world.py`) valida todas as referências cruzadas: destinos de saídas, itens, NPCs, missões/objetivos, habilidades, conquistas, finais, capítulos e posições iniciais. Ids duplicados são erro.
- Verifique com:
  ```bash
  cd backend && uv run python -c "from caneca.game.world import get_world; get_world()"
  uv run pytest
  ```
- Para desambiguar interações sem alvo, use `keywords`; para sugestões, `suggest`; para desfechos alternativos, efeitos com `when`.

## 8. Testes e critérios de qualidade

- Toda mudança de regra ou conteúdo exige teste em `backend/tests/` (cenários determinísticos via `Engine.resolve` com `Intent` explícita ou estado preparado).
- Mudanças de API exigem teste em `tests/test_api.py`; de IA, em `tests/test_ai.py` com `tests/fake_llm.py` (fakes fiéis ao protocolo).
- Antes de concluir: `uv run pytest`, `uv run ruff check caneca`, `npm run lint:web`, `npx tsc -b --noEmit` (em `apps/web`), `npm run build:web`.
- Não marque nada como pronto sem evidência executada. Não invente medições.

Plano completo: [`docs/testing/test-plan.md`](docs/testing/test-plan.md).

## 9. Regras de contribuição

- Commits em **Conventional Commits**: `feat(engine): ...`, `fix(web): ...`, `docs: ...`, `test(api): ...`, `chore(deps): ...`, `refactor(ai): ...`.
- Uma mudança coesa por commit; testes junto com o código.
- Atualize a documentação em `docs/` quando mudar comportamento, contrato ou dados.
- Não remova testes para fazer a suíte passar; não silencie avisos sem justificativa escrita no código.
- Operações destrutivas, publicação e push só com autorização explícita do mantenedor.

## 10. Requisitos de segurança

- Conteúdo gerado por IA e importado é **dado não confiável**: nunca executado, sempre validado/sanitizado; o frontend renderiza texto puro (sem `dangerouslySetInnerHTML`).
- Entradas limitadas (500 caracteres por ação, 256 KiB por requisição, 8 MiB por importação).
- Consultas via SQLAlchemy (parametrizadas).
- CSP restritiva ao servir a PWA; CORS só para origens configuradas; token Bearer opcional (`CANECA_API_TOKEN`).
- Importações validadas contra o schema e o mundo antes de qualquer escrita.
- Modelo de ameaças: [`docs/security/threat-model.md`](docs/security/threat-model.md).
