# Modelo de dados

Fonte: `backend/caneca/persistence/orm.py`, migração `migrations/versions/0001_initial.py`, `backend/caneca/game/state.py`, `backend/caneca/services/saves.py`.

## Banco (SQLite)

Conexões com `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=5000`. Esquema mantido pelo Alembic (`render_as_batch=True`). Ao iniciar, `Database.migrate()` aplica migrações pendentes; se já havia um banco, faz antes um backup `caneca-<data>-pre-migration-<rev>.db` em `<data_dir>/backups` (mantém os 5 mais recentes).

### `games`
| Coluna | Tipo | Notas |
|---|---|---|
| id | String(36) PK | UUID4 |
| name | String(80) | nome da partida |
| created_at, updated_at | DateTime(tz) | UTC |
| state | JSON | `WorldState` completo |
| version | Integer | versão otimista; cada commit faz `WHERE version = esperada` e incrementa |
| turn, chapter, location | Integer/Integer/String(64) | desnormalizados para listagem |
| status | String(16) | `active` · `ended` · `defeated` |
| last_npc | String(64)? | interlocutor do último turno (contexto de conversa) |
| summary, summary_turn | Text, Integer | resumo incremental e o turno em que foi feito |

### `turns`
`id` PK · `game_id` FK (CASCADE) · `number` (único por partida, índice `ix_turns_game_number`) · `created_at` · `kind` (`intro`/`action`) · `player_input` · `intent` JSON · `outcome` JSON (`messages` LText[], `events`, `check`, `success`, `meta`, `minutes`, `dialogue_npc`, `topic`) · `narration` (texto final exibido) · `fallback` (texto do motor no idioma do momento) · `source` (`engine`/`ai`/`fallback`/`cancelled`) · `provider` · `model` · `tokens_in` · `tokens_out`.

Turnos com `source` `engine`/`fallback` são re-renderizados no idioma atual a partir de `outcome.messages`; narrações de IA ficam no idioma em que foram geradas.

### `journal`
`id` · `game_id` FK · `turn` · `kind` (`quest`, `quest_done`, `story`, `chapter`, `ending`, `defeat`) · `title` LText · `body` LText · `location` · `participants` (ids de NPCs presentes) · `decision` (texto da jogadora) · `created_at`. Índice `(game_id, turn)`.

### `checkpoints`
`id` · `game_id` FK · `label` · `turn` · `state` (cópia do documento) · `summary` · `auto` · `created_at`. Criados manualmente, automaticamente na troca de capítulo e antes de cada restauração ("Antes de restaurar").

Restaurar = em uma transação: guarda o ponto atual como checkpoint automático, apaga `turns`/`journal` com turno > checkpoint, copia o estado, incrementa `version`.

### `settings`
`key` PK · `value` JSON. Hoje só `ai` (`AISettings`). Chaves de API **não** ficam aqui (ver `docs/ai/providers.md`).

## `WorldState` (documento da partida)

| Campo | Significado |
|---|---|
| schema_version, content_version, seed | versões e semente dos dados |
| turn, minutes, clock_start | turno; minutos simulados desde o início; hora inicial (min) |
| location, chapter | posição e capítulo |
| mug: `MugIdentity` | nome, cor `#rrggbb`, estilo, material, bebida, personalidade, até 2 traços |
| settings: `AdventureSettings` | tom, dificuldade, tamanho da narração, idioma |
| stats | temperature, coffee, integrity, energy, courage, creativity, xp, level |
| statuses | derivados (hot, lukewarm, cold, overheated, empty, buoyant, tired, cracked, shattered) + narrativos (hidden, wet, watered) |
| abilities, cooldowns | habilidades aprendidas; turnos restantes de recarga |
| visited, discovered | locais visitados; entidades na enciclopédia |
| flags, counters | marcadores livres do conteúdo; contadores |
| **item_locations** | `item_id → onde`: `inventory`, `void`, id de local ou `npc:<id>` |
| npcs | por NPC: location, relationship (−100..100), mood, met, memories (ids de fatos), topics_heard, gifts |
| unlocked_exits | arestas liberadas `origem>destino` |
| quests | status (`inactive`/`active`/`completed`/`failed`), objetivos feitos, desfecho, turnos |
| interactions_done | interações `once` já realizadas |
| achievements, reputation | conquistas; reputação por facção |
| facts | memória de longo prazo: id → texto LText, turno, importância 1–5, local, tags |
| last_event_turn, events_seen | controle de eventos aleatórios |
| ending, defeated | fim da partida |

**Invariante de itens:** cada item tem exatamente uma posição em `item_locations`. Pegar, largar, entregar e consumir só mudam esse valor; não existe lista de inventário separada, logo não há duplicação.

## Arquivo de save exportado (formato v1)

```json
{
  "format": "caneca-quest-save",
  "format_version": 1,
  "app_version": "0.1.0",
  "content_version": "1.0.0",
  "exported_at": "...",
  "game": { "name", "created_at", "status", "state", "summary", "summary_turn", "last_npc" },
  "turns": [ { "number", "kind", "created_at", "player_input", "intent", "outcome", "narration",
               "fallback", "source", "provider", "model", "tokens_in", "tokens_out" } ],
  "journal": [ { "turn", "kind", "title", "body", "location", "participants", "decision", "created_at" } ],
  "checkpoints": [ { "label", "turn", "state", "summary", "auto", "created_at" } ]
}
```

Importação (`services/saves.py::validate_save`): schema estrito (campos extras recusados, limites de tamanho), `format_version` ≤ suportada, versão de conteúdo com mesma *major*, estado e cada checkpoint conferidos contra o mundo (locais, itens e suas posições, NPCs, missões, habilidades, conquistas, final, capítulo, faixas de atributos), turnos sem números duplicados. Só depois a partida é criada com um novo id; arquivos recusados não alteram o banco. Limite de corpo: 8 MiB.
