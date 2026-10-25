# Desempenho do backend — medições reais

Medido em 2026-10-24 com `backend/scripts/bench.py` (modo offline, sem IA). Para reproduzir:

```bash
cd backend
uv run python scripts/bench.py --turns 2000 --json bench.json
```

O script imprime JSON com todos os números; nada é estimado, exceto tokens de prompt (caracteres ÷ 4).

## Máquina

| Item | Valor |
|---|---|
| CPU | AMD Ryzen 7 5700G with Radeon Graphics (16 CPUs lógicas) |
| Memória | 46,4 GiB |
| Sistema | Linux 7.2.12-1-big x86_64 (BigLinux/Manjaro), glibc 2.44 |
| Python | 3.13.15 (venv do `uv`) |
| Banco | SQLite em WAL, arquivo temporário em disco local |

É uma máquina de mesa rápida. Num computador modesto os tempos absolutos serão maiores, mas as folgas abaixo são grandes (uma a duas ordens de grandeza).

## Metas (definidas antes da medição) e resultados

| Medida | Meta | Resultado (p50 / p95) | Situação |
|---|---|---|---|
| Interpretação de texto livre (`Engine.interpret`), 2000 turnos | p95 < 5 ms | 0,21 / 0,32 ms | ✅ |
| Resolução de ação (`Engine.resolve`), 2000 turnos | p95 < 10 ms | 0,38 / 0,54 ms (máx. 1,05 ms) | ✅ |
| Turno completo pela API, offline (`POST /turns?stream=false`), 200 turnos | p95 < 100 ms | 7,3 / 11,2 ms (máx. 91,6 ms, primeiras requisições) | ✅ |
| Inicialização do app (migração + carga do conteúdo YAML) | < 2 s | 25,5 ms (banco novo) | ✅ |
| Carregar partida (`GET /games/{id}`) com 2000 turnos | p95 < 50 ms | 2,7 / 4,0 ms | ✅ |
| Página do histórico mais recente (40 turnos) com 2000 turnos | p95 < 50 ms | 4,2 / 6,9 ms | ✅ |
| Página antiga do histórico (`before=200`) | p95 < 50 ms | 4,2 / 6,6 ms | ✅ |
| Diário (`GET /journal`) | p95 < 50 ms | 2,7 / 4,4 ms | ✅ |
| Lista de partidas | p95 < 50 ms | 2,9 / 4,2 ms | ✅ |
| Exportar partida de 2000 turnos | < 1 s | 98 ms (2,84 MB de JSON) | ✅ |
| Banco com 1 partida de 2000 turnos | < 20 MB | 3,56 MB (inclui WAL) | ✅ |
| Prompt do narrador, partida longa com 300 fatos, contexto 4096 | < 3000 tokens | ≈ 1900 tokens (7603 chars; 11 fatos incluídos, 290 descartados por relevância) | ✅ |
| Prompt, contexto 2048 | cabe com 280 de resposta | ≈ 993 tokens (2 fatos) | ✅ |
| Prompt, contexto 8192 | proporcional ao contexto | ≈ 3772 tokens (57 fatos) | ✅ |
| Memória residente do processo ao final | < 200 MB | 110,5 MB (app + TestClient + benchmark no mesmo processo) | ✅ |

Taxa de crescimento da partida pelo serviço (sem HTTP, com commit transacional por turno): 174 turnos/s.

## Observações

- O custo dominante de um turno offline é a escrita transacional no SQLite (estado + turno + diário), não as regras: o motor leva < 1 ms.
- O histórico é paginado (`limit` ≤ 100) e indexado por `(game_id, number)`; o tempo não cresce de forma perceptível entre a página mais nova e uma antiga.
- O tamanho do prompt é limitado pelo orçamento de memória (`budget_for`): mais fatos registrados não aumentam o prompt, apenas mudam quais fatos entram. Por isso o custo por turno com IA permanece estável em partidas longas.
- Com IA, a latência é dominada pelo modelo (Ollama ou nuvem) e não foi medida aqui: o Ollama não estava instalado neste ambiente. Os testes de integração usam servidores simulados que seguem o protocolo real.
- O valor máximo da API (91,6 ms) ocorre nas primeiras requisições (aquecimento de conexões e caches); p95 fica em 11 ms.
