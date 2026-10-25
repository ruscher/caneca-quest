# Modelo de ameaças

## Ativos

- Partidas salvas (banco SQLite, backups, exportações).
- Chaves de API de provedores em nuvem.
- Integridade das regras (estado só muda pelo motor).
- Máquina do usuário (sistema de arquivos, rede local).
- Privacidade do texto da aventura (enviado a terceiros só com consentimento).

## Fronteiras de confiança

```text
[Jogadora / navegador] ──HTTP──► [API FastAPI] ──► [SQLite / arquivos de dados]
                                      │
                                      └──HTTP──► [Ollama local | provedor em nuvem]   (saída não confiável)
[Arquivo de save importado] ───────► [API]                                          (entrada não confiável)
```

Dados não confiáveis: texto digitado, intenções enviadas pelo cliente, saves importados, qualquer saída de modelo, URLs de provedor configuradas.

## Ameaças e mitigações (STRIDE)

| Ameaça | Mitigação implementada | Onde |
|---|---|---|
| **Injeção de prompt** pelo texto da jogadora | Padrões de injeção detectados pelo parser → turno sem efeito com mensagem fixa; texto inserido no prompt dentro de tags delimitadas, sem `< > [ ] { } \``, limitado a 500 caracteres; instruções de sistema fixas dizem que o bloco é dado | `game/parser.py`, `ai/prompts.py` |
| **Injeção via conteúdo/memória** (narrações antigas, resumos) | Também passam por `sanitize_player_text` antes de entrar no prompt | `ai/prompts.py` |
| **Tampering: IA alterando estado** | IA nunca escreve estado; só narra o RESULTADO OFICIAL já gravado. Intenção refinada pela IA só é aceita se todos os ids pertencem aos candidatos da cena; verbos meta recusados | `ai/orchestrator.py`, `engine._validate_mentions` |
| **Tampering: cliente forjando intenção** | Intenções de sugestão validadas pelo mesmo filtro de candidatos; interação por id só se as condições valem ali | `game/engine.py` |
| **Duplicação/forja de itens** | Posse única em `item_locations`; efeitos só pelo `Mutator` | `game/state.py`, `game/mechanics.py` |
| **Saída de modelo maliciosa ou quebrada** | Remoção de tags, markdown, `<think>`; limites de tamanho; recusas/vazamentos substituídos pelo texto do motor; frontend renderiza texto puro (sem HTML) | `ai/safety.py`, `NarrativeFeed.tsx` |
| **XSS** | Nenhum `dangerouslySetInnerHTML`; CSP `script-src 'self'` sem inline ao servir a PWA; `frame-ancestors 'none'`, `object-src 'none'` | `api/security.py`, `index.html` |
| **Save importado malicioso** | Schema estrito, limites, referências conferidas contra o mundo, faixas de atributos; nada é gravado se falhar; 8 MiB máx. | `services/saves.py` |
| **Acesso por outros programas/sites locais** | Bind padrão `127.0.0.1`; CORS só para origens configuradas; token Bearer opcional (`CANECA_API_TOKEN`, comparação em tempo constante) | `config.py`, `api/security.py`, `main.py` |
| **Negação de serviço** | Corpo ≤ 256 KiB (import 8 MiB, inclusive sem Content-Length); rate limit por cliente (90 req. de escrita/min, configurável); um turno por partida por vez; timeouts e limite de 6000 caracteres no streaming; linha de streaming ≤ 1 MB | `api/security.py`, `services/games.py`, `ai/providers/http_common.py` |
| **Vazamento de credenciais** | Chaves em variável de ambiente ou `secrets.json` 0600 (escrita atômica); API só informa a origem; nunca gravadas no banco nem enviadas ao frontend; `.env`/`secrets.json`/`data/` no `.gitignore` | `ai/config.py` |
| **Envio de dados a terceiros sem consentimento** | Provedores em nuvem ignorados sem `cloud_consent = true`; aviso na UI | `services/games.py`, `SettingsDialog.tsx` |
| **SSRF por URL de provedor** | Só `http(s)` com host; requisições apenas aos caminhos fixos do protocolo; a URL é configurada pelo próprio usuário local. Risco residual: em implantação multiusuário exposta, um usuário poderia apontar o servidor para endereços internos — **não exponha o servidor publicamente sem autenticação** | `ai/providers/http_common.py` |
| **SQL injection** | SQLAlchemy com parâmetros; nenhum SQL montado por concatenação | `services/games.py` |
| **Corrupção do save** | Commit único por turno com versão otimista; WAL; narração gravada depois; backup automático antes de migração e sob demanda (API de backup do SQLite) | `persistence/db.py` |
| **Path traversal no servidor estático** | Arquivo só é servido se estiver dentro de `static_dir` (`resolve()` + verificação de pai) | `main.py` |
| **Repúdio** | Histórico de turnos guarda entrada, intenção, resultado, origem da narração, provedor e modelo | tabela `turns` |

## Desktop (Tauri)

Implementado em `apps/desktop/src-tauri/`:
- **Sem permissões de IPC**: a única capability (`capabilities/main-minimal.json`) tem `permissions: []`; a UI fala com o backend só por HTTP. Nenhum plugin (shell, fs, http) é usado — o sidecar é iniciado pelo próprio Rust com `std::process::Command`.
- **Sidecar isolado**: porta livre escolhida em `127.0.0.1`, `CANECA_API_TOKEN` de 32 bytes aleatórios (`getrandom`) por execução, injetado em `window.__CANECA_RUNTIME__` via `initialization_script`. Sem o token a API responde 401 (verificado com o app em execução).
- **CSP do Tauri**: `connect-src 'self' http://127.0.0.1:*`, `script-src 'self'`, `object-src 'none'`, `frame-ancestors 'none'`.
- **Sem processos órfãos**: o app passa `CANECA_PARENT_PID`; o backend (`caneca/watchdog.py`) desliga sozinho se o app morrer (verificado com `kill -9`). No encerramento normal o app também mata o sidecar.
- **`/tmp` com `noexec`**: o sidecar one-file extrai o Python em `TMPDIR`, que o app aponta para o diretório de cache do usuário.
- Dados do desktop em `app_data_dir` (Linux: `~/.local/share/org.canecaquest.app`).

## Riscos residuais

- Modelos locais podem produzir texto inadequado apesar das instruções; o filtro cobre formato e vazamento, não moderação de conteúdo.
- O rate limit é em memória e por IP; adequado ao uso local, não a uma implantação pública.
- Dependências: revisar com `npm audit` e `uv pip list --outdated`/avisos de segurança antes de cada versão (processo manual; o CI em `.github/workflows/ci.yml` roda lint, tipos e testes, mas não auditoria de dependências).
