# Arquitetura — visão geral

## Componentes

| Componente | Local | Responsabilidade |
|---|---|---|
| Motor de regras | `backend/caneca/game/` | Interpreta intenções, aplica regras, condições e efeitos. Determinístico (dados com semente). |
| Conteúdo do mundo | `backend/caneca/game/content/*.yaml` | Regiões, locais, itens, NPCs, interações, missões, habilidades, eventos, conquistas, finais. Validado na carga. |
| Serviço de partidas | `backend/caneca/services/games.py` | Pipeline de turno, persistência transacional, memória, checkpoints, import/export. |
| Camada de IA | `backend/caneca/ai/` | Prompts, provedores (Ollama, OpenAI-compatível, Anthropic), refinamento de intenção, narração em streaming, resumos, saneamento de saída. |
| Memória | `backend/caneca/memory/context.py` | Seleção de fatos/turnos/resumo dentro de um orçamento de contexto. |
| Persistência | `backend/caneca/persistence/` | SQLite (WAL), SQLAlchemy 2, Alembic, backups pela API de backup do SQLite. |
| API HTTP | `backend/caneca/api/` | REST + SSE, views localizadas, middleware de segurança. |
| Web/PWA | `apps/web/` | Interface React; também é a UI do app desktop. |
| Desktop | `apps/desktop/` | Shell Tauri 2 (Rust). Inicia o backend empacotado (PyInstaller) como sidecar em porta aleatória de `127.0.0.1`, com token por execução, e abre a UI empacotada. |

## Topologia de execução

```text
 ┌───────────────────────────┐          ┌──────────────────────────────────────────┐
 │ Navegador / PWA instalada │  HTTP    │ caneca-server (FastAPI + uvicorn)        │
 │ React + Zustand           │ ───────► │  /api/*  REST + SSE                      │
 │ Service worker (precache) │ ◄─────── │  /*      arquivos da PWA (opcional)      │
 └───────────────────────────┘          │                                          │
                                        │  Engine ── World (YAML validado)         │
 Desenvolvimento: Vite :5173            │  GameService ── SQLite (WAL) + Alembic   │
 com proxy /api → :8765                 │  Narrator ──► Ollama / nuvem (opcional)  │
                                        └──────────────────────────────────────────┘
 Desktop: Tauri carrega a UI empacotada, sobe o sidecar `caneca-server`
 (porta livre, CANECA_API_TOKEN aleatório, CANECA_PARENT_PID) e injeta
 window.__CANECA_RUNTIME__ = { baseUrl, token } antes dos scripts da página.
```

- Padrão: backend em `127.0.0.1:8765`, dados em `~/.local/share/caneca-quest` (Linux), `%APPDATA%\CanecaQuest` (Windows), `~/Library/Application Support/CanecaQuest` (macOS).
- Implantação simples: `caneca-server --static-dir apps/web/dist` serve API e PWA na mesma origem (sem CORS).
- O cliente lê `window.__CANECA_RUNTIME__` (desktop) ou `VITE_API_BASE`; por padrão usa a mesma origem.

## Fluxo de uma ação

```text
POST /api/games/{id}/turns  {text, intent?, expected_turn}
  │
  ├─ bloqueio por partida (uma ação por vez → 409 turn_in_progress)
  ├─ carrega estado + versão (thread)
  ├─ intenção: sugestão (verb/target/item/interaction) | parser | parser + IA (se confiança < 0.6)
  │            └ toda intenção é validada contra os candidatos da cena
  ├─ Engine.resolve(state, intent) → novo estado + eventos + mensagens determinísticas
  ├─ commit transacional: UPDATE games ... WHERE version = esperada
  │                       + INSERT turns + INSERT journal (+ checkpoint automático em troca de capítulo)
  ├─ SSE "outcome"  (view completa, eventos, teste de dados, texto do motor)
  ├─ narração: IA em streaming (SSE "delta"...) ou texto do motor
  ├─ grava narração final (source = ai | fallback | cancelled | engine)
  ├─ SSE "warning" (se a IA falhou) e "done"
  └─ resumo incremental quando devido
```

Cancelamento: o cliente aborta o `fetch` (desconexão) e chama `POST /api/games/{id}/cancel`. O gerador grava a narração parcial ou o texto do motor sob `CancelScope(shield=True)`. O estado já estava salvo.

## Decisões (registro estilo ADR)

1. **Estado como documento único + linhas de eventos.** `games.state` guarda o `WorldState` validado (JSON); turnos, diário e checkpoints são linhas separadas. Um turno é um único commit com verificação otimista de versão. Motivo: atomicidade simples, snapshots triviais (checkpoints = cópia do documento), sem migrações a cada mudança de conteúdo.
2. **Motor determinístico separado da IA.** A IA nunca muda estado; ela recebe o RESULTADO OFICIAL. Dados usam `random.Random(f"{seed}:{turn}:{salt}")`, então a mesma ação nas mesmas condições produz o mesmo resultado (depuração e testes reproduzíveis).
3. **Conteúdo em YAML validado por Pydantic.** Novos locais/missões sem tocar no motor; erros de referência falham na inicialização e nos testes.
4. **Posse de itens em um único mapa** (`item_locations`): duplicação é impossível por construção.
5. **SSE sobre `fetch` POST** em vez de `EventSource` (que só faz GET e não envia corpo nem cabeçalho de autorização). Parser incremental próprio em `apps/web/src/api/sse.ts`.
6. **Sem biblioteca de animação (Motion).** Animações são CSS/SVG e um canvas leve; reduz bundle e custo em máquinas modestas. Respeitam `prefers-reduced-motion` e a preferência do usuário.
7. **i18n próprio e tipado** (`apps/web/src/i18n`). O dicionário inglês tem o tipo do português; chaves ausentes são erro de compilação. Sem dependência extra.
8. **Banco síncrono em threads.** SQLite é local e rápido; `anyio.to_thread` evita bloquear o loop durante streaming.
9. **Sem embeddings no MVP.** Recuperação estruturada por tags/palavras/recência (ver `docs/ai/memory.md`).
10. **Bloqueio de turno por conjunto, não `anyio.Lock`.** O gerador do turno pode ser retomado por outra task durante o streaming; um lock com dono falharia ao liberar.
