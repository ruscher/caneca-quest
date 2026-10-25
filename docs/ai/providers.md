# Provedores de IA

Código: `backend/caneca/ai/` (`config.py`, `providers/`, `orchestrator.py`, `prompts.py`, `safety.py`) e `services/games.py`.

## Modos

| `provider` | O que faz | Dados saem da máquina? |
|---|---|---|
| `offline` (padrão) | Narrativa pré-escrita do motor. Sempre disponível. | Não |
| `ollama` | IA local via Ollama. | Não (a menos que a URL aponte para outra máquina) |
| `openai` | Qualquer API compatível com OpenAI Chat Completions (OpenAI, OpenRouter, Groq, LM Studio, vLLM, llama.cpp server). | Sim, se remota |
| `anthropic` | Anthropic Messages API. | Sim |

Provedores em nuvem só são usados se `cloud_consent = true`; caso contrário o turno usa o modo básico. A UI mostra o aviso de envio a serviço externo e possível cobrança.

## Configuração (`AISettings`, tabela `settings`, chave `ai`)

| Campo | Padrão | Faixa/uso |
|---|---|---|
| provider | `offline` | `offline`/`ollama`/`openai`/`anthropic` |
| models | `{}` | modelo por provedor (`{"ollama": "llama3.2:latest"}`) |
| ollama_url | `http://127.0.0.1:11434` (ou `CANECA_OLLAMA_URL`) | só `http(s)://` |
| openai_base_url | `https://api.openai.com/v1` | só `http(s)://` |
| temperature | 0,8 | 0–1,5 (Anthropic limitada a 1,0) |
| context_tokens | 4096 | 1024–131072 (Ollama: `num_ctx`) |
| timeout_seconds | 90 | 10–600 |
| ai_intent | true | usar a IA para ações ambíguas |
| memory_turns | 4 | 0–12 turnos recentes no prompt |
| summary_every | 12 | turnos entre resumos |
| cloud_consent | false | autorização explícita para nuvem |

## Chaves de API

- Variáveis `CANECA_OPENAI_API_KEY` e `CANECA_ANTHROPIC_API_KEY` têm prioridade.
- Ou `PUT /api/ai/keys/{openai|anthropic}`: gravada em `<data_dir>/secrets.json` com permissão 0600 (escrita atômica). `DELETE` remove.
- A API só informa a origem (`env`/`file`/`null`); a chave nunca é devolvida ao navegador nem gravada no banco.

## Endpoints usados

**Ollama** — `GET /api/version`, `GET /api/tags` (lista modelos instalados; nenhum modelo é presumido), `POST /api/chat` com `stream: true`, `keep_alive: "15m"`, `options {temperature, num_ctx, num_predict, top_p}` e, para intenções, `format: <JSON Schema>`. Resposta NDJSON; uso lido de `prompt_eval_count`/`eval_count`.

**OpenAI-compatível** — `GET {base}/models`, `POST {base}/chat/completions` com `stream: true`, `stream_options.include_usage`, `max_tokens`, e `response_format: json_schema` (strict) para intenções. SSE terminando em `[DONE]`.

**Anthropic** — `GET /v1/models`, `POST /v1/messages` com `anthropic-version: 2023-06-01`, campo `system` separado, `stream: true`; lê `message_start`, `content_block_delta` (`text_delta`), `message_delta` (uso), `message_stop`, `error`.

## Rotas da aplicação

- `GET/PUT /api/ai/settings` · `GET /api/ai/status?provider=` (disponibilidade, modelos, se o modelo escolhido está instalado) · `POST /api/ai/test` (frase curta, mede latência) · `PUT/DELETE /api/ai/keys/{p}` · `GET /api/ai/usage`.

## Chamadas por turno

1. **Refinamento de intenção** (opcional): só quando a confiança do parser < 0,6, a intenção veio de texto livre e não é injeção. Temperatura 0, até 120 tokens, timeout 25 s, saída JSON validada por schema; aceita apenas ids presentes na lista de candidatos da cena. Qualquer falha mantém o resultado do parser.
2. **Narração**: prompt de sistema fixo + bloco de dados (ver `prompts.py`), `max_tokens` por tamanho de narração (curta 130, normal 280, detalhada 450, cinematográfica 700; um nível abaixo para ações simples sem diálogo). Streaming via SSE ao navegador.
3. **Resumo**: a cada `summary_every` turnos, ≤ 260 tokens, temperatura 0,3; sem IA, um resumo determinístico concatena entradas do diário.

## Streaming, cancelamento e falhas

- Deltas passam por `ThinkFilter` (remove `<think>…</think>` mesmo partido entre pedaços) e são limitados a 6000 caracteres.
- Texto final: `clean_narration` remove markdown, listas, blocos de código, tags e "menus de opções"; corta no limite por frase. `acceptable` rejeita textos curtos (< 15 caracteres), recusas ("como uma IA…") e vazamento de instruções. Rejeitado → texto do motor (`source = fallback`).
- Erros do provedor são tipados (`unavailable`, `timeout`, `auth`, `rate_limited`, `model_missing`, `invalid_response`, `bad_request`) e viram evento SSE `warning` (`ai_<código>`) + texto do motor. O turno já estava salvo.
- Cancelamento: abortar o `fetch` ou `POST /api/games/{id}/cancel`. A narração parcial (ou o texto do motor) é gravada com `source = cancelled`.
- Uso de tokens gravado por turno (`tokens_in`, `tokens_out`, provedor, modelo) e agregado em `/api/ai/usage`. Não há cálculo de custo em moeda nem limite de gastos (planejado).

## Instalar o Ollama

Os comandos abaixo são do Ollama, não deste projeto; consulte https://ollama.com para versões atuais.

**BigLinux / Manjaro**
```bash
sudo pacman -S ollama            # ou ollama-cuda (NVIDIA) / ollama-rocm (AMD)
sudo systemctl enable --now ollama
ollama pull llama3.2             # exemplo de modelo pequeno (~2 GB); funciona sem GPU, mais lento
```

**Windows** — instale pelo instalador em https://ollama.com/download; depois, no PowerShell: `ollama pull llama3.2`.

**macOS** — baixe o app em https://ollama.com/download (ou `brew install ollama` e `ollama serve`); depois `ollama pull llama3.2`.

No jogo: Configurações → Inteligência artificial → Ollama → "Verificar e listar modelos" → escolher o modelo → Testar → Salvar.

Modelos maiores (7–8B) narram melhor, mas exigem mais RAM/VRAM e respondem mais devagar em CPU. Modelos com raciocínio (`<think>`) funcionam; o raciocínio é filtrado.

## Estado de validação

Os adaptadores são testados com servidores simulados fiéis aos protocolos (`backend/tests/fake_llm.py`, `tests/test_ai.py`). Até esta versão, **não houve teste contra um Ollama real** no ambiente de desenvolvimento (serviço não instalado), nem contra APIs pagas.
